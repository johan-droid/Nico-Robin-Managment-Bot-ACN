use std::collections::HashMap;
use std::time::{Duration, Instant};

use crate::telegram::api::Bot;
use crate::telegram::update::{ChatPermissions, Message};

use crate::config::Settings;
use crate::handlers::log_mod_action;
use crate::utils::escape_md_v2;

pub struct FloodTracker {
    buckets: HashMap<i64, Vec<Instant>>,
    flood_settings_cache: Option<Option<(i32, String, i32)>>,
}

impl Default for FloodTracker {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct FloodActionInfo {
    pub user_id: u64,
    pub user_name: String,
    pub mode: String,
}

impl FloodTracker {
    pub fn new() -> Self {
        Self {
            buckets: HashMap::new(),
            flood_settings_cache: None,
        }
    }

    pub fn invalidate(&mut self) {
        self.flood_settings_cache = None;
    }

    /// Fetch flood settings from DB and cache in-memory. No-op if already cached.
    pub async fn get_or_fetch_flood_settings(
        &mut self,
        client: &tokio_postgres::Client,
        chat_id: i64,
    ) -> Option<(i32, String, i32)> {
        if chat_id > 0 {
            return None;
        }
        if self.flood_settings_cache.is_none() {
            let fs = crate::db::flood::get_flood_settings(client, chat_id)
                .await
                .ok()
                .flatten();
            self.flood_settings_cache = Some(fs);
        }
        self.flood_settings_cache.clone().flatten()
    }

    /// Evaluates incoming message flood counter purely in-memory.
    /// Does NOT perform any network I/O; lock can be dropped immediately after this call.
    pub fn evaluate_message(
        &mut self,
        msg: &Message,
        flood_settings: Option<(i32, String, i32)>,
    ) -> Option<FloodActionInfo> {
        let user = msg.from()?;
        let user_id = user.id as i64;

        let (limit, mode, window_secs) = match flood_settings {
            Some((limit, mode, window)) if limit > 0 => (limit, mode, window),
            _ => return None,
        };

        let now = Instant::now();
        let window = Duration::from_secs(window_secs as u64);

        let timestamps = self.buckets.entry(user_id).or_default();
        timestamps.retain(|ts| now.duration_since(*ts) < window);
        timestamps.push(now);

        if timestamps.len() > limit as usize {
            self.buckets.remove(&user_id);
            Some(FloodActionInfo {
                user_id: user.id,
                user_name: user.first_name.clone(),
                mode,
            })
        } else {
            None
        }
    }

    /// Periodically evicts stale user bucket entries.
    pub fn cleanup_stale(&mut self, max_age: Duration) {
        let now = Instant::now();
        self.buckets.retain(|_, ts_vec| {
            ts_vec.retain(|ts| now.duration_since(*ts) < max_age);
            !ts_vec.is_empty()
        });
    }
}

/// Executes moderation actions (Telegram API network calls) outside the per-chat Mutex lock.
pub async fn execute_flood_action(
    bot: &Bot,
    msg: &Message,
    action: FloodActionInfo,
    settings: &Settings,
) {
    let user_name = &action.user_name;
    let _ = bot.delete_message(msg.chat.id, msg.id()).await;

    match action.mode.to_lowercase().as_str() {
        "ban" => {
            let _ = bot.ban_chat_member(msg.chat.id, action.user_id).await;
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Banned {} for flooding.", escape_md_v2(user_name)),
                )
                .await;
            log_mod_action(
                bot,
                settings,
                msg.chat.id,
                &format!(
                    "Auto-banned {} in {} for flooding",
                    escape_md_v2(user_name),
                    escape_md_v2(msg.chat.title().unwrap_or("group"))
                ),
            )
            .await;
        }
        "warn" => {
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("⚠️ {}, please stop flooding!", escape_md_v2(user_name)),
                )
                .await;
        }
        _ => {
            let permissions = ChatPermissions::empty();
            let _ = bot
                .restrict_chat_member(msg.chat.id, action.user_id, permissions)
                .await;
            let _ = bot
                .send_message(
                    msg.chat.id,
                    format!("Muted {} for flooding.", escape_md_v2(user_name)),
                )
                .await;
            log_mod_action(
                bot,
                settings,
                msg.chat.id,
                &format!(
                    "Auto-muted {} in {} for flooding",
                    escape_md_v2(user_name),
                    escape_md_v2(msg.chat.title().unwrap_or("group"))
                ),
            )
            .await;
        }
    }
}
