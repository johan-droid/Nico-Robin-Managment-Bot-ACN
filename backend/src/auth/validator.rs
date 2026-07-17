use tracing::warn;

/// Validates and sanitizes user input for the bot.
pub struct InputValidator;

impl InputValidator {
    /// Maximum allowed length for a single message.
    const MAX_MESSAGE_LENGTH: usize = 4096;

    /// Maximum allowed length for a command argument.
    const MAX_ARG_LENGTH: usize = 256;

    /// Maximum number of arguments allowed.
    const MAX_ARGS: usize = 50;

    /// Validates a raw message text.
    /// Returns `None` if the message is invalid, `Some(sanitized)` if valid.
    pub fn validate_message(text: &str) -> Option<String> {
        let text = text.trim();

        // Reject empty messages
        if text.is_empty() {
            warn!("empty_message_rejected");
            return None;
        }

        // Reject excessively long messages
        if text.len() > Self::MAX_MESSAGE_LENGTH {
            warn!(
                length = text.len(),
                max = Self::MAX_MESSAGE_LENGTH,
                "message_too_long_rejected"
            );
            return None;
        }

        // Reject messages with null bytes (potential injection)
        if text.contains('\0') {
            warn!("null_byte_in_message_rejected");
            return None;
        }

        // Reject messages with control characters (except newlines)
        if text
            .chars()
            .any(|c| c.is_control() && c != '\n' && c != '\r')
        {
            warn!("control_characters_in_message_rejected");
            return None;
        }

        // Sanitize: strip leading/trailing whitespace, normalize internal whitespace
        let sanitized = text.split_whitespace().collect::<Vec<_>>().join(" ");

        Some(sanitized)
    }

    /// Validates a command and its arguments.
    /// Returns `None` if invalid, `Some((command, args))` if valid.
    pub fn validate_command(text: &str) -> Option<(String, Vec<String>)> {
        let text = text.trim();

        // Must start with a command prefix
        if !text.starts_with('/') {
            return None;
        }

        // Split into command and args
        let parts: Vec<&str> = text.splitn(2, ' ').collect();
        let command = parts[0].to_lowercase();

        // Validate command name (only alphanumeric and underscores)
        let cmd_name = command.trim_start_matches('/');
        if cmd_name.is_empty() || !cmd_name.chars().all(|c| c.is_alphanumeric() || c == '_') {
            warn!(command = %cmd_name, "invalid_command_name_rejected");
            return None;
        }

        // Validate command length
        if command.len() > Self::MAX_ARG_LENGTH {
            warn!(
                length = command.len(),
                max = Self::MAX_ARG_LENGTH,
                "command_too_long_rejected"
            );
            return None;
        }

        // Parse and validate arguments
        let args = if parts.len() > 1 {
            let args_str = parts[1].trim();
            if args_str.is_empty() {
                Vec::new()
            } else {
                let raw_args: Vec<&str> = args_str.split_whitespace().collect();

                // Reject too many arguments
                if raw_args.len() > Self::MAX_ARGS {
                    warn!(
                        count = raw_args.len(),
                        max = Self::MAX_ARGS,
                        "too_many_arguments_rejected"
                    );
                    return None;
                }

                // Validate each argument
                let mut valid_args = Vec::new();
                for arg in raw_args {
                    if arg.len() > Self::MAX_ARG_LENGTH {
                        warn!(
                            length = arg.len(),
                            max = Self::MAX_ARG_LENGTH,
                            "argument_too_long_rejected"
                        );
                        return None;
                    }
                    if arg.contains('\0') {
                        warn!("null_byte_in_argument_rejected");
                        return None;
                    }
                    valid_args.push(arg.to_string());
                }
                valid_args
            }
        } else {
            Vec::new()
        };

        Some((command, args))
    }

    /// Validates a chat/group ID.
    pub fn validate_chat_id(chat_id: i64) -> bool {
        // Chat IDs should be non-zero
        chat_id != 0
    }

    /// Validates a user ID.
    pub fn validate_user_id(user_id: i64) -> bool {
        // User IDs should be positive
        user_id > 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_message() {
        assert_eq!(
            InputValidator::validate_message("Hello, world!"),
            Some("Hello, world!".to_string())
        );
    }

    #[test]
    fn test_empty_message() {
        assert_eq!(InputValidator::validate_message(""), None);
        assert_eq!(InputValidator::validate_message("   "), None);
    }

    #[test]
    fn test_message_with_null_byte() {
        assert_eq!(InputValidator::validate_message("hello\0world"), None);
    }

    #[test]
    fn test_message_too_long() {
        let long_msg = "a".repeat(5000);
        assert_eq!(InputValidator::validate_message(&long_msg), None);
    }

    #[test]
    fn test_valid_command() {
        let result = InputValidator::validate_command("/start");
        assert!(result.is_some());
        let (cmd, args) = result.unwrap();
        assert_eq!(cmd, "/start");
        assert!(args.is_empty());
    }

    #[test]
    fn test_command_with_args() {
        let result = InputValidator::validate_command("/warn @user spam");
        assert!(result.is_some());
        let (cmd, args) = result.unwrap();
        assert_eq!(cmd, "/warn");
        assert_eq!(args, vec!["@user", "spam"]);
    }

    #[test]
    fn test_invalid_command_name() {
        assert_eq!(InputValidator::validate_command("/bad cmd!"), None);
    }

    #[test]
    fn test_empty_command() {
        assert_eq!(InputValidator::validate_command("/"), None);
    }

    #[test]
    fn test_validate_chat_id() {
        assert!(InputValidator::validate_chat_id(-1001234567890));
        assert!(!InputValidator::validate_chat_id(0));
    }

    #[test]
    fn test_validate_user_id() {
        assert!(InputValidator::validate_user_id(12345));
        assert!(!InputValidator::validate_user_id(0));
        assert!(!InputValidator::validate_user_id(-1));
    }
}
