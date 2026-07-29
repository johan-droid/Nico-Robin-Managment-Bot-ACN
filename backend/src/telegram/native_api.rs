use reqwest::Client;
use serde_json::Value;
use crate::telegram::update::{ChatPermissions, ChatMember};

#[derive(Clone)]
pub struct Bot {
    token: String,
    client: Client,
}

impl Bot {
    pub fn new(token: String) -> Self {
        Self { token, client: Client::new() }
    }

    pub async fn api_post(&self, method: &str, payload: Value) -> Result<Value, String> {
        let url = format!("https://api.telegram.org/bot{}/{}", self.token, method);
        
        sentry::add_breadcrumb(sentry::Breadcrumb {
            category: Some("telegram_api".into()),
            message: Some(format!("Request: {}", method)),
            level: sentry::Level::Info,
            ..Default::default()
        });

        let resp = self
            .client
            .post(&url)
            .json(&payload)
            .send()
            .await
            .map_err(|e| e.to_string())?;

        sentry::add_breadcrumb(sentry::Breadcrumb {
            category: Some("telegram_api".into()),
            message: Some(format!("Response for: {} status={}", method, resp.status())),
            level: sentry::Level::Info,
            ..Default::default()
        });

        let text = resp.text().await.map_err(|e| e.to_string())?;
        let json: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
        if json["ok"].as_bool() == Some(true) {
            Ok(json["result"].clone())
        } else {
            Err(format!("API error: {}", text))
        }
    }

    pub fn client(&self) -> RawClient {
        RawClient {
            token: self.token.clone(),
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
            serde_json::json!({"chat_id": chat_id, "message_id": message_id}),
        )
        .await?;
        Ok(())
    }

    pub async fn ban_chat_member(&self, chat_id: i64, user_id: u64) -> Result<(), String> {
        self.api_post(
            "banChatMember",
            serde_json::json!({"chat_id": chat_id, "user_id": user_id}),
        )
        .await?;
        Ok(())
    }

    pub async fn unban_chat_member(&self, chat_id: i64, user_id: u64) -> Result<(), String> {
        self.api_post(
            "unbanChatMember",
            serde_json::json!({"chat_id": chat_id, "user_id": user_id, "only_if_banned": true}),
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
            serde_json::json!({"chat_id": chat_id, "user_id": user_id, "permissions": permissions}),
        )
        .await?;
        Ok(())
    }

    pub async fn pin_chat_message(&self, chat_id: i64, message_id: u64) -> Result<(), String> {
        self.api_post(
            "pinChatMessage",
            serde_json::json!({"chat_id": chat_id, "message_id": message_id}),
        )
        .await?;
        Ok(())
    }

    pub async fn get_chat_member(
        &self,
        chat_id: i64,
        user_id: u64,
    ) -> Result<ChatMember, String> {
        let res = self
            .api_post(
                "getChatMember",
                serde_json::json!({"chat_id": chat_id, "user_id": user_id}),
            )
            .await?;
        serde_json::from_value(res).map_err(|e| e.to_string())
    }

    pub async fn get_chat_administrators(
        &self,
        chat_id: i64,
    ) -> Result<Vec<ChatMember>, String> {
        let res = self
            .api_post(
                "getChatAdministrators",
                serde_json::json!({"chat_id": chat_id}),
            )
            .await?;
        serde_json::from_value(res).map_err(|e| e.to_string())
    }

    pub async fn get_chat_member_count(&self, chat_id: i64) -> Result<u64, String> {
        let res = self
            .api_post(
                "getChatMemberCount",
                serde_json::json!({"chat_id": chat_id}),
            )
            .await?;
        if let Some(count) = res.as_u64() {
            Ok(count)
        } else {
            Err("Invalid response format".into())
        }
    }

    /// Remove any active webhook so `getUpdates` (long-polling) can receive messages.
    pub async fn delete_webhook(&self, drop_pending_updates: bool) -> Result<(), String> {
        self.api_post(
            "deleteWebhook",
            serde_json::json!({ "drop_pending_updates": drop_pending_updates }),
        )
        .await?;
        Ok(())
    }

    /// Long-poll Telegram for new updates. `timeout` is seconds (Telegram max is 50).
    pub async fn get_updates(
        &self,
        offset: i64,
        timeout: u64,
    ) -> Result<Vec<crate::telegram::update::Update>, String> {
        let res = self
            .api_post(
                "getUpdates",
                serde_json::json!({
                    "offset": offset,
                    "timeout": timeout,
                    "allowed_updates": [
                        "message",
                        "edited_message",
                        "callback_query",
                        "my_chat_member",
                        "chat_member"
                    ]
                }),
            )
            .await?;
        serde_json::from_value(res).map_err(|e| format!("Failed to parse getUpdates: {}", e))
    }
}

pub struct SendMessageBuilder {
    bot: Bot,
    chat_id: i64,
    text: String,
    parse_mode: Option<String>,
}

impl SendMessageBuilder {
    pub fn parse_mode(mut self, parse_mode: crate::telegram::ParseMode) -> Self {
        self.parse_mode = match parse_mode {
            crate::telegram::ParseMode::MarkdownV2 => Some("MarkdownV2".to_string()),
        };
        self
    }
}

impl std::future::IntoFuture for SendMessageBuilder {
    type Output = Result<crate::telegram::update::Message, String>;
    type IntoFuture = std::pin::Pin<Box<dyn std::future::Future<Output = Self::Output> + Send>>;

    fn into_future(self) -> Self::IntoFuture {
        Box::pin(async move {
            let mut payload = serde_json::json!({"chat_id": self.chat_id, "text": self.text});
            if let Some(pm) = self.parse_mode {
                payload["parse_mode"] = serde_json::Value::String(pm);
            }
            let res = self.bot.api_post("sendMessage", payload).await?;
            serde_json::from_value(res).map_err(|e| e.to_string())
        })
    }
}

pub struct RawClient {
    pub token: String,
}

impl RawClient {
    pub fn post(&self, url: &str) -> RawRequestBuilder {
        RawRequestBuilder {
            url: url.to_string(),
            json: None,
            client: Client::new(),
        }
    }
}

pub struct RawRequestBuilder {
    url: String,
    json: Option<Value>,
    client: Client,
}

impl RawRequestBuilder {
    pub fn json(mut self, value: &Value) -> Self {
        self.json = Some(value.clone());
        self
    }

    pub async fn send(self) -> Result<RawResponse, String> {
        let resp = self
            .client
            .post(&self.url)
            .json(&self.json)
            .send()
            .await
            .map_err(|e| e.to_string())?;

        Ok(RawResponse {
            status: resp.status().as_u16(),
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
