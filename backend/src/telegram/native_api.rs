use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;
use reqwest::Client;
use serde_json::Value;
use crate::telegram::update::{ChatPermissions, ChatMember, PhotoSize};

#[derive(Clone)]
pub struct Bot {
    token: String,
    client: Arc<Client>,
    last_messages: Arc<Mutex<HashMap<i64, (i64, Instant)>>>,
}

static SHARED_CLIENT: std::sync::LazyLock<Arc<Client>> = std::sync::LazyLock::new(|| {
    Arc::new(Client::builder()
        .connect_timeout(std::time::Duration::from_secs(10))
        .timeout(std::time::Duration::from_secs(25))
        .pool_max_idle_per_host(20)
        .tcp_keepalive(std::time::Duration::from_secs(30))
        .build()
        .expect("Failed to build reqwest Client"))
});

impl Bot {
    pub fn new(token: String) -> Self {
        Self {
            token,
            client: SHARED_CLIENT.clone(),
            last_messages: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub async fn api_post(&self, method: &str, payload: Value) -> Result<Value, String> {
        let url = format!("https://api.telegram.org/bot{}/{}", self.token, method);

        let resp = self
            .client
            .post(&url)
            .json(&payload)
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

    pub async fn api_post_multipart(&self, method: &str, form: reqwest::multipart::Form) -> Result<Value, String> {
        let url = format!("https://api.telegram.org/bot{}/{}", self.token, method);

        let resp = self
            .client
            .post(&url)
            .multipart(form)
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

    pub fn client(&self) -> RawClient {
        RawClient {
            token: self.token.clone(),
            client: self.client.clone(),
        }
    }

    /// Send a new message or edit the last bot message in this chat.
    pub async fn send_or_edit(
        &self,
        chat_id: i64,
        text: &str,
        parse_mode: Option<crate::telegram::ParseMode>,
        reply_markup: Option<crate::telegram::update::InlineKeyboardMarkup>,
    ) -> Result<crate::telegram::update::Message, String> {
        let pm_str = parse_mode.map(|pm| match pm {
            crate::telegram::ParseMode::MarkdownV2 => "MarkdownV2".to_string(),
            crate::telegram::ParseMode::Html => "HTML".to_string(),
        });

        // Only attempt edit if the tracked message is < 30 seconds old.
        // Stale messages (old commands, previous sessions) skip edit
        // and send fresh, avoiding a guaranteed-fail Telegram API call.
        let should_edit = self.last_messages.lock().ok()
            .and_then(|m| m.get(&chat_id).copied())
            .filter(|&(_, ts)| ts.elapsed() < std::time::Duration::from_secs(30))
            .is_some();

        if should_edit {
            let (msg_id, _ts) = self.last_messages.lock().ok().and_then(|mut m| m.remove(&chat_id)).unwrap();
            let mut payload = serde_json::json!({
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": text,
            });
            if let Some(ref pm) = pm_str {
                payload["parse_mode"] = serde_json::Value::String(pm.clone());
            }
            if let Some(ref rm) = reply_markup {
                payload["reply_markup"] = serde_json::to_value(rm).map_err(|e| e.to_string())?;
            }
            match self.api_post("editMessageText", payload).await {
                Ok(res) => {
                    if let Ok(msg) = serde_json::from_value::<crate::telegram::update::Message>(res) {
                        if let Ok(mut m) = self.last_messages.lock() {
                            m.insert(chat_id, (msg.id() as i64, Instant::now()));
                        }
                        return Ok(msg);
                    }
                    if let Ok(mut m) = self.last_messages.lock() {
                        m.insert(chat_id, (msg_id, Instant::now()));
                    }
                    return Err("edit succeeded but response not a Message".into());
                }
                Err(_) => {}
            }
        }

        let mut payload = serde_json::json!({
            "chat_id": chat_id,
            "text": text,
        });
        if let Some(ref pm) = pm_str {
            payload["parse_mode"] = serde_json::Value::String(pm.clone());
        }
        if let Some(ref rm) = reply_markup {
            payload["reply_markup"] = serde_json::to_value(rm).map_err(|e| e.to_string())?;
        }
        let res = self.api_post("sendMessage", payload).await?;
        let msg: crate::telegram::update::Message = serde_json::from_value(res).map_err(|e| e.to_string())?;
        if let Ok(mut m) = self.last_messages.lock() {
            m.insert(chat_id, (msg.id() as i64, Instant::now()));
        }
        Ok(msg)
    }

    pub fn clear_last_message(&self, chat_id: i64) {
        if let Ok(mut m) = self.last_messages.lock() {
            m.remove(&chat_id);
        }
    }

    pub fn reply_or_edit(&self, chat_id: i64, text: impl Into<String>) -> EditOrSendBuilder {
        EditOrSendBuilder {
            bot: self.clone(),
            chat_id,
            text: text.into(),
            parse_mode: None,
            reply_markup: None,
        }
    }

    pub fn send_message(&self, chat_id: i64, text: impl Into<String>) -> SendMessageBuilder {
        SendMessageBuilder {
            bot: self.clone(),
            chat_id,
            text: text.into(),
            parse_mode: None,
            reply_markup: None,
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

    /// Bans a user for a duration. `until_date` is a Unix timestamp (seconds).
    pub async fn ban_chat_member_until(
        &self,
        chat_id: i64,
        user_id: u64,
        until_date: i64,
    ) -> Result<(), String> {
        self.api_post(
            "banChatMember",
            serde_json::json!({
                "chat_id": chat_id,
                "user_id": user_id,
                "until_date": until_date,
                "revoke_messages": false,
            }),
        )
        .await?;
        Ok(())
    }

    /// Restricts a user until `until_date` (Unix timestamp, seconds).
    pub async fn restrict_chat_member_until(
        &self,
        chat_id: i64,
        user_id: u64,
        permissions: ChatPermissions,
        until_date: i64,
    ) -> Result<(), String> {
        self.api_post(
            "restrictChatMember",
            serde_json::json!({
                "chat_id": chat_id,
                "user_id": user_id,
                "permissions": permissions,
                "until_date": until_date,
            }),
        )
        .await?;
        Ok(())
    }

    /// Bulk-deletes up to 100 messages in one call.
    pub async fn delete_messages(&self, chat_id: i64, message_ids: Vec<u64>) -> Result<(), String> {
        for chunk in message_ids.chunks(100) {
            let ids: Vec<i64> = chunk.iter().map(|&id| id as i64).collect();
            let _ = self
                .api_post(
                    "deleteMessages",
                    serde_json::json!({"chat_id": chat_id, "message_ids": ids}),
                )
                .await?;
        }
        Ok(())
    }

    pub async fn unban_chat_member(&self, chat_id: i64, user_id: u64) -> Result<(), String> {
        self.api_post(
            "unbanChatMember",
            serde_json::json!({"chat_id": chat_id, "user_id": user_id, "only_if_banned": false}),
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

    pub async fn unpin_chat_message(&self, chat_id: i64, message_id: u64) -> Result<(), String> {
        self.api_post(
            "unpinChatMessage",
            serde_json::json!({"chat_id": chat_id, "message_id": message_id}),
        )
        .await?;
        Ok(())
    }

    pub async fn unpin_all_chat_messages(&self, chat_id: i64) -> Result<(), String> {
        self.api_post(
            "unpinAllChatMessages",
            serde_json::json!({"chat_id": chat_id}),
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

    /// Fetch a user's most recent profile photo (largest available size).
    pub async fn get_user_profile_photo(&self, user_id: u64) -> Result<Option<PhotoSize>, String> {
        let res = self
            .api_post(
                "getUserProfilePhotos",
                serde_json::json!({"user_id": user_id, "limit": 1}),
            )
            .await?;
        let photos = res
            .get("photos")
            .and_then(|p| p.as_array())
            .cloned()
            .unwrap_or_default();
        let Some(most_recent) = photos.first() else {
            return Ok(None);
        };
        let sizes: Vec<PhotoSize> =
            serde_json::from_value(most_recent.clone()).map_err(|e| e.to_string())?;
        Ok(sizes.into_iter().max_by_key(|p| p.width))
    }

    /// Resolve a Telegram `file_id` to a downloadable `file_path`.
    pub async fn get_file_path(&self, file_id: &str) -> Result<String, String> {
        let res = self
            .api_post("getFile", serde_json::json!({"file_id": file_id}))
            .await?;
        res.get("file_path")
            .and_then(|p| p.as_str())
            .map(|s| s.to_string())
            .ok_or_else(|| "Failed to parse file_path".to_string())
    }

    /// Download raw bytes from Telegram's file CDN (`api.telegram.org/file/bot<token>/<path>`).
    pub async fn download_file(&self, file_path: &str) -> Result<Vec<u8>, String> {
        let url = format!(
            "https://api.telegram.org/file/bot{}/{}",
            self.token, file_path
        );
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| e.to_string())?;
        if !resp.status().is_success() {
            return Err(format!(
                "File download failed with status {}",
                resp.status()
            ));
        }
        resp.bytes().await.map(|b| b.to_vec()).map_err(|e| e.to_string())
    }

    pub async fn delete_webhook(&self, drop_pending_updates: bool) -> Result<(), String> {
        self.api_post(
            "deleteWebhook",
            serde_json::json!({ "drop_pending_updates": drop_pending_updates }),
        )
        .await?;
        Ok(())
    }

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

    pub async fn export_chat_invite_link(&self, chat_id: i64) -> Result<String, String> {
        let res = self
            .api_post(
                "exportChatInviteLink",
                serde_json::json!({ "chat_id": chat_id }),
            )
            .await?;
        res.as_str()
            .map(|s| s.to_string())
            .ok_or_else(|| "Failed to parse invite link as string".to_string())
    }

    pub async fn answer_callback_query(&self, callback_query_id: &str) -> Result<(), String> {
        self.api_post(
            "answerCallbackQuery",
            serde_json::json!({"callback_query_id": callback_query_id}),
        )
        .await?;
        Ok(())
    }

    pub fn send_photo(&self, chat_id: i64, photo: impl Into<String>) -> SendPhotoBuilder {
        SendPhotoBuilder {
            bot: self.clone(),
            chat_id,
            photo: photo.into(),
            caption: None,
            parse_mode: None,
            reply_markup: None,
        }
    }

    pub async fn send_sticker(
        &self,
        chat_id: i64,
        filename: &str,
        data: Vec<u8>,
    ) -> Result<crate::telegram::update::Message, String> {
        let form = reqwest::multipart::Form::new()
            .text("chat_id", chat_id.to_string())
            .part(
                "sticker",
                reqwest::multipart::Part::bytes(data)
                    .file_name(filename.to_string())
                    .mime_str("image/webp")
                    .map_err(|e| e.to_string())?,
            );

        let res = self.api_post_multipart("sendSticker", form).await?;
        serde_json::from_value(res).map_err(|e| e.to_string())
    }

    pub async fn send_photo_file(
        &self,
        chat_id: i64,
        filename: &str,
        data: Vec<u8>,
        caption: Option<String>,
        parse_mode: Option<crate::telegram::ParseMode>,
        reply_markup: Option<crate::telegram::update::InlineKeyboardMarkup>,
    ) -> Result<crate::telegram::update::Message, String> {
        let mime = if filename.to_lowercase().ends_with(".png") {
            "image/png"
        } else {
            "image/jpeg"
        };
        let mut form = reqwest::multipart::Form::new()
            .text("chat_id", chat_id.to_string())
            .part(
                "photo",
                reqwest::multipart::Part::bytes(data)
                    .file_name(filename.to_string())
                    .mime_str(mime)
                    .map_err(|e| e.to_string())?,
            );

        if let Some(cap) = caption {
            form = form.text("caption", cap);
        }

        if let Some(pm) = parse_mode {
            let pm_str = match pm {
                crate::telegram::ParseMode::MarkdownV2 => "MarkdownV2",
                crate::telegram::ParseMode::Html => "HTML",
            };
            form = form.text("parse_mode", pm_str.to_string());
        }

        if let Some(rm) = reply_markup {
            let rm_str = serde_json::to_string(&rm).map_err(|e| e.to_string())?;
            form = form.text("reply_markup", rm_str);
        }

        let res = self.api_post_multipart("sendPhoto", form).await?;
        serde_json::from_value(res).map_err(|e| e.to_string())
    }
}

pub struct SendPhotoBuilder {
    bot: Bot,
    chat_id: i64,
    photo: String,
    caption: Option<String>,
    parse_mode: Option<String>,
    reply_markup: Option<crate::telegram::update::InlineKeyboardMarkup>,
}

impl SendPhotoBuilder {
    pub fn caption(mut self, caption: Option<String>) -> Self {
        self.caption = caption;
        self
    }

    pub fn parse_mode(mut self, parse_mode: crate::telegram::ParseMode) -> Self {
        self.parse_mode = match parse_mode {
            crate::telegram::ParseMode::MarkdownV2 => Some("MarkdownV2".to_string()),
            crate::telegram::ParseMode::Html => Some("HTML".to_string()),
        };
        self
    }

    pub fn reply_markup(mut self, markup: crate::telegram::update::InlineKeyboardMarkup) -> Self {
        self.reply_markup = Some(markup);
        self
    }
}

impl std::future::IntoFuture for SendPhotoBuilder {
    type Output = Result<crate::telegram::update::Message, String>;
    type IntoFuture = std::pin::Pin<Box<dyn std::future::Future<Output = Self::Output> + Send>>;

    fn into_future(self) -> Self::IntoFuture {
        Box::pin(async move {
            let mut payload = serde_json::json!({
                "chat_id": self.chat_id,
                "photo": self.photo
            });
            if let Some(caption) = self.caption {
                payload["caption"] = serde_json::Value::String(caption);
            }
            if let Some(pm) = self.parse_mode {
                payload["parse_mode"] = serde_json::Value::String(pm);
            }
            if let Some(rm) = &self.reply_markup {
                payload["reply_markup"] = serde_json::to_value(rm).map_err(|e| e.to_string())?;
            }
            let res = self.bot.api_post("sendPhoto", payload).await?;
            serde_json::from_value(res).map_err(|e| e.to_string())
        })
    }
}

pub struct SendMessageBuilder {
    bot: Bot,
    chat_id: i64,
    text: String,
    parse_mode: Option<String>,
    reply_markup: Option<crate::telegram::update::InlineKeyboardMarkup>,
}

impl SendMessageBuilder {
    pub fn parse_mode(mut self, parse_mode: crate::telegram::ParseMode) -> Self {
        self.parse_mode = match parse_mode {
            crate::telegram::ParseMode::MarkdownV2 => Some("MarkdownV2".to_string()),
            crate::telegram::ParseMode::Html => Some("HTML".to_string()),
        };
        self
    }

    pub fn reply_markup(mut self, markup: crate::telegram::update::InlineKeyboardMarkup) -> Self {
        self.reply_markup = Some(markup);
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
            if let Some(rm) = &self.reply_markup {
                payload["reply_markup"] = serde_json::to_value(rm).map_err(|e| e.to_string())?;
            }
            let res = self.bot.api_post("sendMessage", payload).await?;
            serde_json::from_value(res).map_err(|e| e.to_string())
        })
    }
}

pub struct EditOrSendBuilder {
    bot: Bot,
    chat_id: i64,
    text: String,
    parse_mode: Option<String>,
    reply_markup: Option<crate::telegram::update::InlineKeyboardMarkup>,
}

impl EditOrSendBuilder {
    pub fn parse_mode(mut self, parse_mode: crate::telegram::ParseMode) -> Self {
        self.parse_mode = match parse_mode {
            crate::telegram::ParseMode::MarkdownV2 => Some("MarkdownV2".to_string()),
            crate::telegram::ParseMode::Html => Some("HTML".to_string()),
        };
        self
    }

    pub fn reply_markup(mut self, markup: crate::telegram::update::InlineKeyboardMarkup) -> Self {
        self.reply_markup = Some(markup);
        self
    }
}

impl std::future::IntoFuture for EditOrSendBuilder {
    type Output = Result<crate::telegram::update::Message, String>;
    type IntoFuture = std::pin::Pin<Box<dyn std::future::Future<Output = Self::Output> + Send>>;

    fn into_future(self) -> Self::IntoFuture {
        Box::pin(async move {
            let pm = self.parse_mode.map(|s| match s.as_str() {
                "MarkdownV2" => crate::telegram::ParseMode::MarkdownV2,
                "HTML" => crate::telegram::ParseMode::Html,
                _ => crate::telegram::ParseMode::MarkdownV2,
            });
            self.bot.send_or_edit(self.chat_id, &self.text, pm, self.reply_markup).await
        })
    }
}

pub struct RawClient {
    pub token: String,
    pub client: Arc<Client>,
}

impl RawClient {
    pub fn post(&self, url: &str) -> RawRequestBuilder {
        RawRequestBuilder {
            url: url.to_string(),
            json: None,
            client: self.client.clone(),
        }
    }
}

pub struct RawRequestBuilder {
    url: String,
    json: Option<Value>,
    client: Arc<Client>,
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
