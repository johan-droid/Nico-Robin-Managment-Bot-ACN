pub mod flood_tracker;
pub mod rate_limiter;

use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

struct AdminCacheEntry {
    is_admin: bool,
    expires_at: Instant,
}

static ADMIN_CACHE: std::sync::LazyLock<Mutex<HashMap<(i64, u64), AdminCacheEntry>>> =
    std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));

pub fn is_sudo_or_privileged(user_id: u64) -> bool {
    if let Ok(sudo_val) = std::env::var("SUDO_USERS") {
        for id_str in sudo_val.split(',') {
            if let Ok(id) = id_str.trim().parse::<u64>() {
                if id == user_id {
                    return true;
                }
            }
        }
    }
    if let Ok(captain_val) = std::env::var("CAPTAIN_ID") {
        if let Ok(id) = captain_val.trim().parse::<u64>() {
            if id == user_id {
                return true;
            }
        }
    }
    if let Ok(commander_val) = std::env::var("COMMANDER_IDS") {
        for id_str in commander_val.split(',') {
            if let Ok(id) = id_str.trim().parse::<u64>() {
                if id == user_id {
                    return true;
                }
            }
        }
    }
    false
}

/// Checks if a user is authorized to execute a command.
/// Uses Telegram group admin status with a 300-second in-memory TTL cache.
pub async fn is_telegram_admin(bot: &Bot, chat_id: i64, user_id: u64) -> bool {
    if is_sudo_or_privileged(user_id) {
        return true;
    }

    // In private chats (chat_id > 0), the user is always authorized.
    if chat_id > 0 {
        return true;
    }

    let key = (chat_id, user_id);
    let now = Instant::now();

    if let Ok(cache) = ADMIN_CACHE.lock() {
        if let Some(entry) = cache.get(&key) {
            if entry.expires_at > now {
                return entry.is_admin;
            }
        }
    }

    let is_admin = match bot.get_chat_member(chat_id, user_id).await {
        Ok(member) => {
            let status = member.status();
            matches!(status, "creator" | "administrator")
        }
        Err(_) => false,
    };

    if let Ok(mut cache) = ADMIN_CACHE.lock() {
        cache.insert(
            key,
            AdminCacheEntry {
                is_admin,
                expires_at: now + Duration::from_secs(300),
            },
        );
    }

    is_admin
}

/// Checks if a user is the group captain (creator / owner) or a developer.
/// Only the group creator and privileged users (SUDO_USERS / CAPTAIN_ID /
/// COMMANDER_IDS) pass; ordinary admins and members do not.
pub async fn is_captain_or_developer(bot: &Bot, chat_id: i64, user_id: u64) -> bool {
    if is_sudo_or_privileged(user_id) {
        return true;
    }
    // In private chats there is no group owner — only the developer may act.
    if chat_id > 0 {
        return false;
    }
    match bot.get_chat_member(chat_id, user_id).await {
        Ok(member) => member.status() == "creator",
        Err(_) => false,
    }
}

/// Extracts the target user ID from a reply, message entity (text_mention), or command arguments.
pub fn extract_target_user(msg: &Message) -> Option<(i64, String)> {
    if let Some(reply_to) = msg.reply_to_message() {
        if let Some(from) = reply_to.from() {
            return Some((from.id as i64, from.first_name.clone()));
        }
    }

    if let Some(entities) = msg.entities() {
        for entity in entities {
            if entity.type_ == "text_mention" {
                if let Some(user) = &entity.user {
                    return Some((user.id as i64, user.first_name.clone()));
                }
            }
        }
    }

    if let Some(reply_to) = msg.reply_to_message() {
        if let Some(entities) = reply_to.entities() {
            for entity in entities {
                if entity.type_ == "text_mention" {
                    if let Some(user) = &entity.user {
                        return Some((user.id as i64, user.first_name.clone()));
                    }
                }
            }
        }
    }

    if let Some(text) = msg.text() {
        let parts: Vec<&str> = text.split_whitespace().collect();
        if parts.len() >= 2 {
            let target = parts[1];
            if target.starts_with('@') {
                return Some((0, target.to_string()));
            }
            if let Ok(id) = target.parse::<i64>() {
                return Some((id, id.to_string()));
            }
        }
    }

    None
}

/// Attempts to resolve a @username to a user ID within the given chat.
pub async fn resolve_username(bot: &Bot, chat_id: i64, username: &str) -> Option<(i64, String)> {
    let clean_uname = username.trim_start_matches('@').to_lowercase();
    if clean_uname.is_empty() {
        return None;
    }
    if let Ok(admins) = bot.get_chat_administrators(chat_id).await {
        for admin in admins {
            let u = admin.user;
            if let Some(ref un) = u.username {
                if un.to_lowercase() == clean_uname {
                    return Some((u.id as i64, u.first_name));
                }
            }
        }
    }
    None
}
