pub mod flood_tracker;
pub mod rate_limiter;

use teloxide::prelude::*;

use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

struct AdminCacheEntry {
    is_admin: bool,
    expires_at: Instant,
}

static ADMIN_CACHE: std::sync::LazyLock<Mutex<HashMap<(i64, u64), AdminCacheEntry>>> =
    std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));

/// Checks if a user is authorized to execute a command.
/// Uses Telegram group admin status with a 60-second in-memory TTL cache to prevent API rate limits.
/// Group owners and administrators can use all admin commands directly.
pub async fn is_telegram_admin(bot: &Bot, chat_id: ChatId, user_id: UserId) -> bool {
    let key = (chat_id.0, user_id.0);
    let now = Instant::now();

    if let Ok(cache) = ADMIN_CACHE.lock() {
        if let Some(entry) = cache.get(&key) {
            if entry.expires_at > now {
                return entry.is_admin;
            }
        }
    }

    let is_admin = match bot.get_chat_member(chat_id, user_id).await {
        Ok(member) => matches!(
            member.status(),
            teloxide::types::ChatMemberStatus::Owner
                | teloxide::types::ChatMemberStatus::Administrator
        ),
        Err(_) => false,
    };

    if let Ok(mut cache) = ADMIN_CACHE.lock() {
        cache.insert(
            key,
            AdminCacheEntry {
                is_admin,
                expires_at: now + Duration::from_secs(60),
            },
        );
    }

    is_admin
}

/// Extracts the target user ID from a reply, message entity (text_mention), or command arguments.
/// Returns (user_id, display_name).
pub fn extract_target_user(msg: &Message) -> Option<(i64, String)> {
    // First check if this is a reply to another message
    if let Some(reply_to) = msg.reply_to_message() {
        if let Some(from) = reply_to.from() {
            return Some((from.id.0 as i64, from.first_name.clone()));
        }
    }

    // Check for text_mention entities (resolved @usernames)
    if let Some(entities) = msg.entities() {
        for entity in entities {
            if let teloxide::types::MessageEntityKind::TextMention { user } = &entity.kind {
                return Some((user.id.0 as i64, user.first_name.clone()));
            }
        }
    }

    // Also check entities on the replied-to message
    if let Some(reply_to) = msg.reply_to_message() {
        if let Some(entities) = reply_to.entities() {
            for entity in entities {
                if let teloxide::types::MessageEntityKind::TextMention { user } = &entity.kind {
                    return Some((user.id.0 as i64, user.first_name.clone()));
                }
            }
        }
    }

    // Fall back to numeric ID or @username (username won't resolve — returns 0)
    if let Some(text) = msg.text() {
        let parts: Vec<&str> = text.split_whitespace().collect();
        if parts.len() >= 2 {
            let target = parts[1];
            if target.starts_with('@') {
                // Cannot resolve @username without Telegram API call — return 0 to signal failure
                return Some((0, target.to_string()));
            }
            if let Ok(id) = target.parse::<i64>() {
                return Some((id, id.to_string()));
            }
        }
    }

    None
}

/// Attempts to resolve a @username to a user ID within the given chat (e.g. from chat administrators).
pub async fn resolve_username(bot: &Bot, chat_id: ChatId, username: &str) -> Option<(i64, String)> {
    let clean_uname = username.trim_start_matches('@').to_lowercase();
    if clean_uname.is_empty() {
        return None;
    }
    if let Ok(admins) = bot.get_chat_administrators(chat_id).await {
        for admin in admins {
            let u = admin.user;
            if let Some(ref un) = u.username {
                if un.to_lowercase() == clean_uname {
                    return Some((u.id.0 as i64, u.first_name));
                }
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {

    #[test]
    fn test_extract_target_user_from_reply() {
        // This is a basic test for the admin detection function
        // Actual Telegram API calls are tested via integration tests
    }
}
