use crate::telegram::update::{ChatMember, ChatPermissions, PhotoSize};
use reqwest::Client;
use serde_json::Value;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;

#[derive(Clone)]
pub struct Bot {
    token: String,
    client: Arc<Client>,
    last_messages: Arc<Mutex<HashMap<i64, (i64, Instant)>>>,
    /// Per-chat menu message that all in-place UI navigation edits
    /// (`/start`, `/help`, category callbacks). Value: (message_id, is_photo).
    menu_messages: Arc<Mutex<HashMap<i64, (i64, bool)>>>,
}

static SHARED_CLIENT: std::sync::LazyLock<Arc<Client>> = std::sync::LazyLock::new(|| {
    Arc::new(
        Client::builder()
            .connect_timeout(std::time::Duration::from_secs(10))
            .timeout(std::time::Duration::from_secs(60))
            .pool_max_idle_per_host(20)
            .tcp_keepalive(std::time::Duration::from_secs(30))
            .build()
            .expect("Failed to build reqwest Client"),
    )
});

/// Token bucket that bounds how fast the bot may call the Telegram API.
/// Telegram enforces roughly 30 requests/second per bot; exceeding it causes
/// cascading 429 responses and can lead to temporary lockouts. Every outbound
/// call passes through `acquire()` so no handler can flood the API.
struct TelegramRateLimiter {
    rate: f64,
    burst: f64,
    state: Mutex<(f64, Instant)>,
}

impl TelegramRateLimiter {
    fn new(rate_per_sec: f64) -> Self {
        Self {
            rate: rate_per_sec,
            burst: rate_per_sec,
            state: Mutex::new((rate_per_sec, Instant::now())),
        }
    }

    async fn acquire(&self) {
        loop {
            let wait = {
                let mut g = self.state.lock().unwrap_or_else(|e| e.into_inner());
                let now = Instant::now();
                let (mut tokens, last) = *g;
                let elapsed = now.duration_since(last).as_secs_f64();
                tokens = (tokens + elapsed * self.rate).min(self.burst);
                let wait = if tokens >= 1.0 {
                    0.0
                } else {
                    (1.0 - tokens) / self.rate
                };
                *g = (if tokens >= 1.0 { tokens - 1.0 } else { tokens }, now);
                wait
            };
            if wait <= 0.0 {
                return;
            }
            tokio::time::sleep(std::time::Duration::from_secs_f64(wait.min(1.0))).await;
        }
    }
}

static TELEGRAM_RATE_LIMITER: std::sync::LazyLock<TelegramRateLimiter> =
    std::sync::LazyLock::new(|| {
        let rate = std::env::var("TELEGRAM_RATE_LIMIT")
            .ok()
            .and_then(|v| v.parse::<f64>().ok())
            .filter(|r| *r >= 1.0)
            .unwrap_or(30.0);
        TelegramRateLimiter::new(rate)
    });

async fn rate_limit_telegram() {
    TELEGRAM_RATE_LIMITER.acquire().await;
}

/// Methods that are NOT idempotent: a 429 retry of one of these would mint a
/// duplicate side effect (e.g. a fresh invite link). These are never auto-retried.
fn is_retryable(method: &str) -> bool {
    !matches!(
        method,
        "exportChatInviteLink" | "createChatInviteLink" | "revokeChatInviteLink"
    )
}

impl Bot {
    pub fn new(token: String) -> Self {
        Self {
            token,
            client: SHARED_CLIENT.clone(),
            last_messages: Arc::new(Mutex::new(HashMap::new())),
            menu_messages: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub async fn get_me(&self) -> Result<crate::telegram::update::User, String> {
        let res = self.api_post("getMe", serde_json::json!({})).await?;
        serde_json::from_value(res).map_err(|e| format!("Failed to parse getMe: {}", e))
    }

    pub async fn api_post(&self, method: &str, payload: Value) -> Result<Value, String> {
        rate_limit_telegram().await;
        let url = format!("https://api.telegram.org/bot{}/{}", self.token, method);
        let mut retries = 0;

        loop {
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
                return Ok(json["result"].clone());
            }

            let error_code = json["error_code"].as_i64().unwrap_or(0);
            if error_code == 429 && retries < 2 && is_retryable(method) {
                // Honor Telegram's real backoff (can exceed 10s during a
                // lockout); the previous hard 10s cap fought the API.
                let retry_after = json["parameters"]["retry_after"]
                    .as_u64()
                    .unwrap_or(1)
                    .min(120);
                tokio::time::sleep(std::time::Duration::from_secs(retry_after)).await;
                // Re-acquire the token bucket between retries instead of letting
                // the retry burst through the limiter.
                rate_limit_telegram().await;
                retries += 1;
                continue;
            }

            return Err(format!("API error: {}", text));
        }
    }

    pub async fn api_post_multipart(
        &self,
        method: &str,
        form: reqwest::multipart::Form,
    ) -> Result<Value, String> {
        rate_limit_telegram().await;
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
        let should_edit = self
            .last_messages
            .lock()
            .ok()
            .and_then(|m| m.get(&chat_id).copied())
            .filter(|&(_, ts)| ts.elapsed() < std::time::Duration::from_secs(30))
            .is_some();

        if should_edit {
            let (msg_id, _ts) = self
                .last_messages
                .lock()
                .ok()
                .and_then(|mut m| m.remove(&chat_id))
                .unwrap();
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
            if let Ok(res) = self.api_post("editMessageText", payload).await {
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
        let msg: crate::telegram::update::Message =
            serde_json::from_value(res).map_err(|e| e.to_string())?;
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

    /// Remember which message hosts the bot's navigable menu for this chat.
    /// `is_photo` tells callers whether edits must go through `editMessageCaption`.
    pub fn track_menu(&self, chat_id: i64, message_id: i64, is_photo: bool) {
        if let Ok(mut m) = self.menu_messages.lock() {
            m.insert(chat_id, (message_id, is_photo));
        }
    }

    /// Look up the tracked menu message for this chat, if any.
    pub fn tracked_menu(&self, chat_id: i64) -> Option<(i64, bool)> {
        self.menu_messages
            .lock()
            .ok()
            .and_then(|m| m.get(&chat_id).copied())
    }

    /// Edit an existing message in place, using `editMessageCaption` for photo
    /// messages and `editMessageText` otherwise. Re-tracks the menu message on
    /// success so later edits keep targeting the same message.
    pub async fn edit_menu_message(
        &self,
        chat_id: i64,
        message_id: i64,
        is_photo: bool,
        text: &str,
        parse_mode: Option<crate::telegram::ParseMode>,
        reply_markup: Option<crate::telegram::update::InlineKeyboardMarkup>,
    ) -> Result<crate::telegram::update::Message, String> {
        let method = if is_photo {
            "editMessageCaption"
        } else {
            "editMessageText"
        };
        let field = if is_photo { "caption" } else { "text" };
        let pm_str = parse_mode.map(|pm| match pm {
            crate::telegram::ParseMode::MarkdownV2 => "MarkdownV2",
            crate::telegram::ParseMode::Html => "HTML",
        });

        let mut payload = serde_json::json!({
            "chat_id": chat_id,
            "message_id": message_id,
            field: text,
        });
        if let Some(ref pm) = pm_str {
            payload["parse_mode"] = serde_json::Value::String(pm.to_string());
        }
        if let Some(ref rm) = reply_markup {
            payload["reply_markup"] = serde_json::to_value(rm).map_err(|e| e.to_string())?;
        }
        let res = self.api_post(method, payload).await?;
        let msg: crate::telegram::update::Message =
            serde_json::from_value(res).map_err(|e| e.to_string())?;
        self.track_menu(chat_id, message_id, is_photo);
        Ok(msg)
    }

    /// Edit the chat's tracked menu message (`/start` photo or help message) to
    /// show a new page, keeping navigation on a single message. Falls back to
    /// sending a fresh text message when nothing is tracked or the edit fails.
    pub async fn edit_menu_or_send(
        &self,
        chat_id: i64,
        text: &str,
        parse_mode: Option<crate::telegram::ParseMode>,
        reply_markup: Option<crate::telegram::update::InlineKeyboardMarkup>,
    ) -> Result<crate::telegram::update::Message, String> {
        if let Some((message_id, is_photo)) = self.tracked_menu(chat_id) {
            if let Ok(msg) = self
                .edit_menu_message(
                    chat_id,
                    message_id,
                    is_photo,
                    text,
                    parse_mode,
                    reply_markup.clone(),
                )
                .await
            {
                return Ok(msg);
            }
        }

        let pm_str = parse_mode.map(|pm| match pm {
            crate::telegram::ParseMode::MarkdownV2 => "MarkdownV2".to_string(),
            crate::telegram::ParseMode::Html => "HTML".to_string(),
        });
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
        let msg: crate::telegram::update::Message =
            serde_json::from_value(res).map_err(|e| e.to_string())?;
        self.track_menu(chat_id, msg.id() as i64, false);
        Ok(msg)
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

    pub async fn get_chat_member(&self, chat_id: i64, user_id: u64) -> Result<ChatMember, String> {
        let res = self
            .api_post(
                "getChatMember",
                serde_json::json!({"chat_id": chat_id, "user_id": user_id}),
            )
            .await?;
        serde_json::from_value(res).map_err(|e| e.to_string())
    }

    pub async fn get_chat_administrators(&self, chat_id: i64) -> Result<Vec<ChatMember>, String> {
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
            self.bot
                .send_or_edit(self.chat_id, &self.text, pm, self.reply_markup)
                .await
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
