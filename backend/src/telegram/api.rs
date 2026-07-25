use serde_json::Value;
use worker::{Fetch, Headers, Method, Request};

use super::update::ChatPermissions;

#[derive(Clone)]
pub struct Bot {
    token: String,
}

impl Bot {
    pub fn new(token: String) -> Self {
        Self { token }
    }

    pub fn client(&self) -> RawClient {
        RawClient {
            token: self.token.clone(),
        }
    }

    async fn api_post(&self, method: &str, payload: Value) -> Result<Value, String> {
        let url = format!("https://api.telegram.org/bot{}/{}", self.token, method);

        let mut headers = Headers::new();
        headers.set("Content-Type", "application/json").unwrap();

        let req = Request::new_with_init(
            &url,
            &worker::RequestInit {
                method: Method::Post,
                headers,
                body: Some(worker::wasm_bindgen::JsValue::from_str(
                    &payload.to_string(),
                )),
                ..Default::default()
            },
        )
        .map_err(|e| e.to_string())?;

        let mut resp = Fetch::Request(req)
            .send()
            .await
            .map_err(|e| e.to_string())?;

        let text = resp.text().await.map_err(|e| e.to_string())?;

        let json: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
        if json["ok"].as_bool() == Some(true) {
            Ok(json["result"].clone())
        } else {
            Err(format!("API error: {}", text))
        }
    }

    pub fn send_message(&self, chat_id: i64, text: impl Into<String>) -> SendMessageBuilder {
        SendMessageBuilder {
            bot: self.clone(),
            chat_id,
            text: text.into(),
            parse_mode: None,
        }
    }

    pub async fn delete_message(&self, chat_id: i64, message_id: u64) -> Result<(), String> {
        self.api_post(
            "deleteMessage",
            serde_json::json!({
                "chat_id": chat_id,
                "message_id": message_id
            }),
        )
        .await?;
        Ok(())
    }

    pub async fn ban_chat_member(&self, chat_id: i64, user_id: u64) -> Result<(), String> {
        self.api_post(
            "banChatMember",
            serde_json::json!({
                "chat_id": chat_id,
                "user_id": user_id
            }),
        )
        .await?;
        Ok(())
    }

    pub async fn unban_chat_member(&self, chat_id: i64, user_id: u64) -> Result<(), String> {
        self.api_post(
            "unbanChatMember",
            serde_json::json!({
                "chat_id": chat_id,
                "user_id": user_id,
                "only_if_banned": true
            }),
        )
        .await?;
        Ok(())
    }

    pub async fn restrict_chat_member(
        &self,
        chat_id: i64,
        user_id: u64,
        permissions: ChatPermissions,
    ) -> Result<(), String> {
        self.api_post(
            "restrictChatMember",
            serde_json::json!({
                "chat_id": chat_id,
                "user_id": user_id,
                "permissions": permissions
            }),
        )
        .await?;
        Ok(())
    }

    pub async fn pin_chat_message(&self, chat_id: i64, message_id: u64) -> Result<(), String> {
        self.api_post(
            "pinChatMessage",
            serde_json::json!({
                "chat_id": chat_id,
                "message_id": message_id
            }),
        )
        .await?;
        Ok(())
    }

    pub async fn get_chat_member(
        &self,
        chat_id: i64,
        user_id: u64,
    ) -> Result<super::update::ChatMember, String> {
        let res = self
            .api_post(
                "getChatMember",
                serde_json::json!({
                    "chat_id": chat_id,
                    "user_id": user_id
                }),
            )
            .await?;
        serde_json::from_value(res).map_err(|e| e.to_string())
    }

    pub async fn get_chat_administrators(
        &self,
        chat_id: i64,
    ) -> Result<Vec<super::update::ChatMember>, String> {
        let res = self
            .api_post(
                "getChatAdministrators",
                serde_json::json!({
                    "chat_id": chat_id
                }),
            )
            .await?;
        serde_json::from_value(res).map_err(|e| e.to_string())
    }

    pub async fn get_chat_member_count(&self, chat_id: i64) -> Result<u64, String> {
        let res = self
            .api_post(
                "getChatMemberCount",
                serde_json::json!({
                    "chat_id": chat_id
                }),
            )
            .await?;
        if let Some(count) = res.as_u64() {
            Ok(count)
        } else {
            Err("Invalid response format".into())
        }
    }
}

pub struct SendMessageBuilder {
    bot: Bot,
    chat_id: i64,
    text: String,
    parse_mode: Option<String>,
}

impl SendMessageBuilder {
    pub fn parse_mode(mut self, parse_mode: ParseMode) -> Self {
        self.parse_mode = match parse_mode {
            ParseMode::MarkdownV2 => Some("MarkdownV2".to_string()),
        };
        self
    }
}

// Remove `Send` requirement so Wasm futures don't complain
impl std::future::IntoFuture for SendMessageBuilder {
    type Output = Result<super::update::Message, String>;
    type IntoFuture = std::pin::Pin<Box<dyn std::future::Future<Output = Self::Output>>>;

    fn into_future(self) -> Self::IntoFuture {
        Box::pin(async move {
            let mut payload = serde_json::json!({
                "chat_id": self.chat_id,
                "text": self.text
            });
            if let Some(pm) = self.parse_mode {
                payload["parse_mode"] = serde_json::Value::String(pm);
            }
            let res = self.bot.api_post("sendMessage", payload).await?;
            serde_json::from_value(res).map_err(|e| e.to_string())
        })
    }
}

pub enum ParseMode {
    MarkdownV2,
}

pub struct RawClient {
    #[allow(dead_code)] pub token: String,
}

impl RawClient {
    pub fn post(&self, url: &str) -> RawRequestBuilder {
        RawRequestBuilder {
            url: url.to_string(),
            json: None,
        }
    }
}

pub struct RawRequestBuilder {
    url: String,
    json: Option<Value>,
}

impl RawRequestBuilder {
    pub fn json(mut self, value: &Value) -> Self {
        self.json = Some(value.clone());
        self
    }

    pub async fn send(self) -> Result<RawResponse, String> {
        let mut headers = Headers::new();
        headers.set("Content-Type", "application/json").unwrap();

        let body = self
            .json
            .map(|v| worker::wasm_bindgen::JsValue::from_str(&v.to_string()));

        let req = Request::new_with_init(
            &self.url,
            &worker::RequestInit {
                method: Method::Post,
                headers,
                body,
                ..Default::default()
            },
        )
        .map_err(|e| e.to_string())?;

        let resp = Fetch::Request(req)
            .send()
            .await
            .map_err(|e| e.to_string())?;

        Ok(RawResponse {
            status: resp.status_code(),
        })
    }
}

pub struct RawResponse {
    status: u16,
}

impl RawResponse {
    pub fn status(&self) -> RawStatus {
        RawStatus { code: self.status }
    }
}

pub struct RawStatus {
    code: u16,
}

impl RawStatus {
    pub fn is_success(&self) -> bool {
        self.code >= 200 && self.code < 300
    }
}
