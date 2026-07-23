use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

use teloxide::prelude::*;
use teloxide::types::UserId;

use crate::config::Settings;
use crate::handlers::log_mod_action;
use crate::utils::escape_md_v2;

pub struct FloodTracker {
    buckets: RwLock<HashMap<(i64, i64), Vec<Instant>>>,
    settings_cache: RwLock<HashMap<i64, Option<(i32, String, i32)>>>,
}

pub type SharedFloodTracker = Arc<FloodTracker>;

impl FloodTracker {
    pub fn new() -> Self {
        Self {
            buckets: RwLock::new(HashMap::new()),
            settings_cache: RwLock::new(HashMap::new()),
        }
    }

    /// Invalidates cached flood settings for a given chat ID (e.g. when setflood is updated).
    pub async fn invalidate(&self, chat_id: i64) {
        let mut cache = self.settings_cache.write().await;
        cache.remove(&chat_id);
    }

    /// Checks if a user message violates group flood settings.
    /// If violated, takes action (mute/ban/warn), deletes message, and returns true.
    pub async fn process_message(
        &self,
        bot: &Bot,
        msg: &Message,
        pool: &sqlx::PgPool,
        settings: &Settings,
    ) -> bool {
        let user_id = match msg.from() {
            Some(u) => u.id.0 as i64,
            None => return false,
        };
        let chat_id = msg.chat.id.0;

        // Check in-memory flood settings cache first
        let cached = {
            let cache = self.settings_cache.read().await;
            cache.get(&chat_id).cloned()
        };

        let flood_settings = match cached {
            Some(opt) => opt,
            None => {
                let db_res = crate::db::flood::get_flood_settings(pool, chat_id)
                    .await
                    .ok()
                    .flatten();
                let mut cache = self.settings_cache.write().await;
                cache.insert(chat_id, db_res.clone());
                db_res
            }
        };

        let (limit, mode, window_secs) = match flood_settings {
            Some((limit, mode, window)) if limit > 0 => (limit, mode, window),
            _ => return false,
        };

        let now = Instant::now();
        let window = Duration::from_secs(window_secs as u64);

        let is_flooding = {
            let mut buckets = self.buckets.write().await;
            let timestamps = buckets.entry((chat_id, user_id)).or_default();
            timestamps.retain(|ts| now.duration_since(*ts) < window);
            timestamps.push(now);
            timestamps.len() > limit as usize
        };

        if is_flooding {
            let user_name = msg.from().map(|u| u.first_name.as_str()).unwrap_or("User");
            let _ = bot.delete_message(msg.chat.id, msg.id).await;

            match mode.to_lowercase().as_str() {
                "ban" => {
                    let _ = bot
                        .ban_chat_member(msg.chat.id, UserId(user_id as u64))
                        .await;
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
                    // Default action: MUTE
                    let permissions = teloxide::types::ChatPermissions::empty();
                    let _ = bot
                        .restrict_chat_member(msg.chat.id, UserId(user_id as u64), permissions)
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
            return true;
        }

        false
    }

    pub async fn cleanup(&self, max_age_secs: u64) {
        let now = Instant::now();
        let max_age = Duration::from_secs(max_age_secs);
        {
            let mut buckets = self.buckets.write().await;
            buckets.retain(|_, timestamps| {
                timestamps.retain(|ts| now.duration_since(*ts) < max_age);
                !timestamps.is_empty()
            });
        }
        {
            let mut cache = self.settings_cache.write().await;
            cache.clear();
        }
    }
}
