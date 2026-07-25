use std::collections::HashMap;
use std::time::{Duration, Instant};

use crate::telegram::api::Bot;
use crate::telegram::update::{ChatPermissions, Message};

use crate::config::Settings;
use crate::handlers::log_mod_action;
use crate::utils::escape_md_v2;

#[allow(dead_code)]
pub struct FloodTracker {
    buckets: HashMap<i64, Vec<Instant>>,
    settings_cache: Option<(i32, String, i32)>,
}

#[allow(dead_code)]
impl FloodTracker {
    #[allow(dead_code)]
    pub fn new() -> Self {
        Self {
            buckets: HashMap::new(),
            settings_cache: None,
        }
    }

    pub fn invalidate(&mut self) {
        self.settings_cache = None;
    }

    pub fn update_cache(&mut self, settings: Option<(i32, String, i32)>) {
        self.settings_cache = settings;
    }

    pub fn get_cache(&self) -> Option<Option<(i32, String, i32)>> {
        // Return Some(None) if cached as no-settings, None if missing cache
        // But for simplicity, let's just make the caller pass it in via process_message instead.
        None
    }

    /// Checks if a user message violates group flood settings.
    /// If violated, takes action (mute/ban/warn), deletes message, and returns true.
    pub async fn process_message(
        &mut self,
        bot: &Bot,
        msg: &Message,
        flood_settings: Option<(i32, String, i32)>,
        settings: &Settings,
    ) -> bool {
        let user_id = match msg.from() {
            Some(u) => u.id as i64,
            None => return false,
        };

        let (limit, mode, window_secs) = match flood_settings {
            Some((limit, mode, window)) if limit > 0 => (limit, mode, window),
            _ => return false,
        };

        let now = Instant::now();
        let window = Duration::from_secs(window_secs as u64);

        let timestamps = self.buckets.entry(user_id).or_default();
        timestamps.retain(|ts| now.duration_since(*ts) < window);
        timestamps.push(now);
        let is_flooding = timestamps.len() > limit as usize;

        if is_flooding {
            let user_name = msg.from().map(|u| u.first_name.as_str()).unwrap_or("User");
            let _ = bot.delete_message(msg.chat.id, msg.id()).await;

            match mode.to_lowercase().as_str() {
                "ban" => {
                    let _ = bot.ban_chat_member(msg.chat.id, user_id as u64).await;
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
                    let permissions = ChatPermissions::empty();
                    let _ = bot
                        .restrict_chat_member(msg.chat.id, user_id as u64, permissions)
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
}
