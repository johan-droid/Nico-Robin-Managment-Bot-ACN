pub mod rate_limiter;
pub mod redactor;
pub mod validator;

use crate::config::Settings;

/// Role-based access control for the bot.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[allow(dead_code)]
pub enum UserRole {
    Normal,
    Commander,
    Captain,
    Sudo,
}

/// Determines the role of a user based on configured IDs.
#[allow(dead_code)]
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
#[allow(dead_code)]
pub fn require_role(user_id: i64, required_role: UserRole, settings: &Settings) -> bool {
    let user_role = get_user_role(user_id, settings);
    role_rank(user_role) >= role_rank(required_role)
}

/// Checks if a chat/group is in the allowed list.
#[allow(dead_code)]
pub fn is_group_allowed(chat_id: i64, settings: &Settings) -> bool {
    // If no allowed groups are configured, allow all
    if settings.allowed_group_ids.is_empty() {
        return true;
    }
    settings.allowed_group_ids.contains(&chat_id)
}

#[allow(dead_code)]
fn role_rank(role: UserRole) -> u8 {
    match role {
        UserRole::Normal => 0,
        UserRole::Commander => 1,
        UserRole::Captain => 2,
        UserRole::Sudo => 3,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_settings() -> Settings {
        // Minimal settings for testing
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
        assert!(require_role(100, UserRole::Captain, &settings)); // sudo can do captain
        assert!(require_role(50, UserRole::Commander, &settings)); // captain can do commander
        assert!(!require_role(999, UserRole::Commander, &settings)); // normal cannot
    }

    #[test]
    fn test_group_allowed() {
        let settings = test_settings();
        assert!(is_group_allowed(-100, &settings));
        assert!(is_group_allowed(200, &settings));
        assert!(!is_group_allowed(999, &settings));
    }
}
