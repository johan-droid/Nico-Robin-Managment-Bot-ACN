pub mod rate_limiter;
pub mod flood_tracker;

use crate::config::Settings;
use teloxide::prelude::*;

/// Role-based access control for the bot.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UserRole {
    Normal,
    Commander,
    Captain,
    Sudo,
}

/// Determines the role of a user based on configured IDs.
pub fn get_user_role(user_id: i64, settings: &Settings) -> UserRole {
    if settings.sudo_users.contains(&user_id) {
        return UserRole::Sudo;
    }
    if settings.captain_id == user_id {
        return UserRole::Captain;
    }
    if settings.commander_ids.contains(&user_id) {
        return UserRole::Commander;
    }
    UserRole::Normal
}

/// Checks if a user is authorized to execute a command that requires a minimum role.
pub fn require_role(user_id: i64, required_role: UserRole, settings: &Settings) -> bool {
    let user_role = get_user_role(user_id, settings);
    role_rank(user_role) >= role_rank(required_role)
}

fn role_rank(role: UserRole) -> u8 {
    match role {
        UserRole::Normal => 0,
        UserRole::Commander => 1,
        UserRole::Captain => 2,
        UserRole::Sudo => 3,
    }
}

/// Checks if a user is an admin/creator in a Telegram chat using the bot API.
pub async fn is_telegram_admin(bot: &Bot, chat_id: ChatId, user_id: UserId) -> bool {
    match bot.get_chat_member(chat_id, user_id).await {
        Ok(member) => matches!(
            member.status(),
            teloxide::types::ChatMemberStatus::Owner
                | teloxide::types::ChatMemberStatus::Administrator
        ),
        Err(_) => false,
    }
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
    use super::*;

    fn test_settings() -> Settings {
        serde_json::from_value(serde_json::json!({
            "bot_token": "test:token",
            "database_url": "postgres://localhost/test",
            "sudo_users": "100,200",
            "captain_id": 50,
            "commander_ids": "30,40",
            "allowed_group_ids": "-100,200",
        }))
        .unwrap()
    }

    #[test]
    fn test_sudo_role() {
        let settings = test_settings();
        assert_eq!(get_user_role(100, &settings), UserRole::Sudo);
        assert_eq!(get_user_role(200, &settings), UserRole::Sudo);
    }

    #[test]
    fn test_captain_role() {
        let settings = test_settings();
        assert_eq!(get_user_role(50, &settings), UserRole::Captain);
    }

    #[test]
    fn test_commander_role() {
        let settings = test_settings();
        assert_eq!(get_user_role(30, &settings), UserRole::Commander);
        assert_eq!(get_user_role(40, &settings), UserRole::Commander);
    }

    #[test]
    fn test_normal_role() {
        let settings = test_settings();
        assert_eq!(get_user_role(999, &settings), UserRole::Normal);
    }

    #[test]
    fn test_require_role() {
        let settings = test_settings();
        assert!(require_role(100, UserRole::Captain, &settings));
        assert!(require_role(50, UserRole::Commander, &settings));
        assert!(!require_role(999, UserRole::Commander, &settings));
    }

}
