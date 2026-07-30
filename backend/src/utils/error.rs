use std::fmt;
use std::fs;
use std::path::Path;
use chrono::Utc;

#[derive(Debug)]
pub enum BotError {
    ValidationError(String),
    AuthError(String),
    TelegramError(String),
    DatabaseError(String),
    NetworkError(String),
    Timeout(String),
    ConfigError(String),
    Unexpected(String),
}

impl fmt::Display for BotError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BotError::ValidationError(s) => write!(f, "Validation Error: {}", s),
            BotError::AuthError(s) => write!(f, "Auth Error: {}", s),
            BotError::TelegramError(s) => write!(f, "Telegram API Error: {}", s),
            BotError::DatabaseError(s) => write!(f, "Database Error: {}", s),
            BotError::NetworkError(s) => write!(f, "Network Error: {}", s),
            BotError::Timeout(s) => write!(f, "Timeout: {}", s),
            BotError::ConfigError(s) => write!(f, "Configuration Error: {}", s),
            BotError::Unexpected(s) => write!(f, "Unexpected Error: {}", s),
        }
    }
}

impl std::error::Error for BotError {}

impl From<tokio_postgres::Error> for BotError {
    fn from(err: tokio_postgres::Error) -> Self {
        BotError::DatabaseError(err.to_string())
    }
}

impl From<reqwest::Error> for BotError {
    fn from(err: reqwest::Error) -> Self {
        BotError::NetworkError(err.to_string())
    }
}

impl From<serde_json::Error> for BotError {
    fn from(err: serde_json::Error) -> Self {
        BotError::ValidationError(err.to_string())
    }
}

pub fn report_failure(err: &BotError, trace_id: u64, component: &str, operation: &str) {
    let dir = Path::new("diagnostics/failures");
    if let Err(e) = fs::create_dir_all(dir) {
        eprintln!("Failed to create diagnostics/failures directory: {}", e);
        return;
    }

    let timestamp = Utc::now().to_rfc3339();
    let filename = format!("failure_{}_{}.md", Utc::now().format("%Y%m%d_%H%M%S"), trace_id);
    let filepath = dir.join(filename);

    let logs = crate::utils::logging::LOG_BUFFER.try_with(|buf| {
        buf.borrow().join("\n")
    }).unwrap_or_else(|_| "No trace logs recorded".to_string());

    let sanitized_err = sanitize_secrets(&err.to_string());
    let sanitized_logs = sanitize_secrets(&logs);

    let report = format!(
        "# Failure Report\n\n\
         - **Timestamp**: {}\n\
         - **Trace ID**: {}\n\
         - **Component**: {}\n\
         - **Operation**: {}\n\
         - **Error Type**: {:?}\n\n\
         ## Error Message\n\
         ```\n\
         {}\n\
         ```\n\n\
         ## Related Execution Logs\n\
         ```\n\
         {}\n\
         ```\n",
        timestamp, trace_id, component, operation, err, sanitized_err, sanitized_logs
    );

    if let Err(e) = fs::write(&filepath, report) {
        eprintln!("Failed to write failure report: {}", e);
    }

    sentry::configure_scope(|scope| {
        scope.set_tag("trace_id", trace_id.to_string());
        scope.set_tag("component", component);
        scope.set_tag("operation", operation);
    });
    sentry::capture_message(&format!("Failure: {}", sanitized_err), sentry::Level::Error);
}

pub fn sanitize_secrets(input: &str) -> String {
    let mut output = input.to_string();
    if let Ok(token) = std::env::var("BOT_TOKEN") {
        if !token.is_empty() {
            output = output.replace(&token, "[REDACTED_BOT_TOKEN]");
        }
    }
    if let Ok(db_url) = std::env::var("DATABASE_URL") {
        if !db_url.is_empty() {
            output = output.replace(&db_url, "[REDACTED_DATABASE_URL]");
        }
    }
    if let Ok(secret) = std::env::var("WEBHOOK_SECRET") {
        if !secret.is_empty() {
            output = output.replace(&secret, "[REDACTED_WEBHOOK_SECRET]");
        }
    }
    if let Ok(secret_path) = std::env::var("WEBHOOK_SECRET_PATH") {
        if !secret_path.is_empty() {
            output = output.replace(&secret_path, "[REDACTED_WEBHOOK_SECRET_PATH]");
        }
    }
    output
}
