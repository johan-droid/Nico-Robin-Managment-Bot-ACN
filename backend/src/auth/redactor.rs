use std::sync::OnceLock;

/// A set of patterns/k keys that should be redacted when logging.
static SENSITIVE_KEYS: OnceLock<Vec<&'static str>> = OnceLock::new();

/// Returns the list of sensitive key substrings to redact.
fn sensitive_keys() -> &'static Vec<&'static str> {
    SENSITIVE_KEYS.get_or_init(|| {
        vec![
            "bot_token",
            "token",
            "database_url",
            "DATABASE_URL",
            "BOT_TOKEN",
            "redis_url",
            "REDIS_URL",
            "webhook_secret",
            "metrics_api_key",
            "data_encryption_key",
            "password",
            "secret",
            "api_key",
            "api_key",
            "authorization",
            "Authorization",
        ]
    })
}

/// Redacts sensitive information from a log message string.
/// Replaces sensitive values with "[REDACTED]".
pub fn redact_sensitive(input: &str) -> String {
    let mut result = input.to_string();

    // Redact common patterns like `key=value` or `key: value` or `"key"="value"`
    for key in sensitive_keys() {
        // Pattern: key=<value> (e.g., bot_token=abc123)
        let patterns = [
            format!(r#""{}"\s*[:=]\s*"[^"]*""#, regex_escape(key)),
            format!(r#"{}[:=]\S+"#, regex_escape(key)),
            format!(r#"{}:\s*"[^"]*""#, regex_escape(key)),
        ];

        for _pattern in &patterns {
            // Since we can't use regex crate directly, do a simpler approach:
            // Find occurrences of the key followed by = or : and redact the value
            let key_equals = format!("{}=", key);
            let key_colon = format!("{}:", key);
            let key_json = format!("\"{}\":", key);

            while let Some(pos) = result.find(&key_json) {
                let end = result[pos..].find(',').unwrap_or(result.len() - pos);
                let end = result[pos..].find('}').map(|e| e.min(end)).unwrap_or(end) + pos;
                result.replace_range(pos..=end, &format!("{} [REDACTED]", key_json));
            }

            while let Some(pos) = result.find(&key_equals) {
                let val_start = pos + key_equals.len();
                let remaining = &result[val_start..];
                // Find end of value (space, comma, brace, or end of string)
                let val_end = remaining
                    .find(|c: char| {
                        c == ' ' || c == ',' || c == '}' || c == '"' || c == '\n' || c == '\r'
                    })
                    .unwrap_or(remaining.len());
                if val_end > 0 && val_end <= 50 {
                    // Only redact if value looks like a real value (not a key name)
                    result.replace_range(val_start..val_start + val_end, "[REDACTED]");
                } else {
                    break;
                }
            }

            if let Some(pos) = result.find(&key_colon) {
                let val_start = pos + key_colon.len();
                let remaining = &result[val_start..];
                let trimmed = remaining.trim_start();
                if let Some(val_end) = trimmed.find([' ', ',', '}', '\n', '\r']) {
                    let abs_start = val_start + (remaining.len() - trimmed.len());
                    let val = &trimmed[..val_end];
                    if !val.is_empty() && val.len() <= 50 {
                        result.replace_range(abs_start..abs_start + val_end, "[REDACTED]");
                    }
                }
            }
        }
    }

    result
}

/// Helper to escape special regex characters for literal matching.
fn regex_escape(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            '\\' => "\\\\".to_string(),
            '.' => "\\.".to_string(),
            '+' => "\\+".to_string(),
            '*' => "\\*".to_string(),
            '?' => "\\?".to_string(),
            '(' => "\\(".to_string(),
            ')' => "\\)".to_string(),
            '[' => "\\[".to_string(),
            ']' => "\\]".to_string(),
            '{' => "\\{".to_string(),
            '}' => "\\}".to_string(),
            '^' => "\\^".to_string(),
            '$' => "\\$".to_string(),
            '|' => "\\|".to_string(),
            '/' => "\\/".to_string(),
            _ => c.to_string(),
        })
        .collect()
}

/// A wrapper for sensitive string values that redacts them in Debug/Display.
#[derive(Clone)]
#[allow(dead_code)]
pub struct SecretString(String);

#[allow(dead_code)]
impl SecretString {
    pub fn new(value: String) -> Self {
        Self(value)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }

    pub fn into_inner(self) -> String {
        self.0
    }
}

impl std::fmt::Debug for SecretString {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[REDACTED]")
    }
}

impl std::fmt::Display for SecretString {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[REDACTED]")
    }
}

impl From<String> for SecretString {
    fn from(s: String) -> Self {
        Self(s)
    }
}

impl From<&str> for SecretString {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}

impl std::ops::Deref for SecretString {
    type Target = str;

    fn deref(&self) -> &str {
        &self.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_redact_bot_token_env() {
        let input = "BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11";
        let redacted = redact_sensitive(input);
        assert!(!redacted.contains("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"));
        assert!(redacted.contains("[REDACTED]"));
    }

    #[test]
    fn test_redact_in_json() {
        let input = r#"{"bot_token": "secret_token_123", "other": "value"}"#;
        let redacted = redact_sensitive(input);
        assert!(!redacted.contains("secret_token_123"));
        assert!(redacted.contains("[REDACTED]"));
    }

    #[test]
    fn test_secret_string_debug() {
        let secret = SecretString::new("supersecret".to_string());
        let debug_str = format!("{:?}", secret);
        assert_eq!(debug_str, "[REDACTED]");
    }

    #[test]
    fn test_secret_string_display() {
        let secret = SecretString::new("supersecret".to_string());
        let display_str = format!("{}", secret);
        assert_eq!(display_str, "[REDACTED]");
    }

    #[test]
    fn test_redact_database_url() {
        let input = "DATABASE_URL=postgres://user:password@localhost:5432/db";
        let redacted = redact_sensitive(input);
        assert!(!redacted.contains("postgres://user:password@localhost:5432/db"));
        assert!(redacted.contains("[REDACTED]"));
    }

    #[test]
    fn test_no_false_positives() {
        let input = "Using token_bucket algorithm for rate limiting";
        let redacted = redact_sensitive(input);
        // Should not redact 'token' in 'token_bucket' or similar safe contexts aggressively
        assert!(redacted.contains("token_bucket"));
    }
}
