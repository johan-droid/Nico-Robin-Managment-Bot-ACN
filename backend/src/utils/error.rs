use chrono::Utc;
use std::fmt;
use std::fs;
use std::path::Path;

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

pub async fn report_failure(err: &BotError, trace_id: u64, component: &str, operation: &str) {
    let dir = Path::new("diagnostics/failures");

    let timestamp = Utc::now().to_rfc3339();
    let filename = format!(
        "failure_{}_{}.md",
        Utc::now().format("%Y%m%d_%H%M%S"),
        trace_id
    );
    let filepath = dir.join(filename);

    let logs = crate::utils::logging::LOG_BUFFER
        .try_with(|buf| buf.borrow().join("\n"))
        .unwrap_or_else(|_| "No trace logs recorded".to_string());

    // Redact secrets from BOTH the debug type line and the message body so a
    // secret inside a handler error string never lands on disk in plaintext.
    let sanitized_debug = sanitize_secrets(&format!("{:?}", err));
    let sanitized_err = sanitize_secrets(&err.to_string());
    let sanitized_logs = sanitize_secrets(&logs);

    let report = format!(
        "# Failure Report\n\n\
         - **Timestamp**: {}\n\
         - **Trace ID**: {}\n\
         - **Component**: {}\n\
         - **Operation**: {}\n\
         - **Error Type**: {}\n\n\
         ## Error Message\n\
         ```\n\
         {}\n\
         ```\n\n\
         ## Related Execution Logs\n\
         ```\n\
         {}\n\
         ```\n",
        timestamp, trace_id, component, operation, sanitized_debug, sanitized_err, sanitized_logs
    );

    // File I/O off the async worker thread.
    let dir_owned = dir.to_path_buf();
    let filepath_owned = filepath.clone();
    let report_owned = report.clone();
    let _ = tokio::task::spawn_blocking(move || {
        if let Err(e) = fs::create_dir_all(&dir_owned) {
            eprintln!("Failed to create diagnostics/failures directory: {}", e);
            return;
        }
        if let Err(e) = fs::write(&filepath_owned, &report_owned) {
            eprintln!("Failed to write failure report: {}", e);
        }
    })
    .await;

    sentry::configure_scope(|scope| {
        scope.set_tag("trace_id", trace_id.to_string());
        scope.set_tag("component", component);
        scope.set_tag("operation", operation);
    });
    sentry::capture_message(&format!("Failure: {}", sanitized_err), sentry::Level::Error);
}

pub fn sanitize_secrets(input: &str) -> String {
    let mut output = input.to_string();
    for key in [
        "BOT_TOKEN",
        "DATABASE_URL",
        "WEBHOOK_SECRET",
        "WEBHOOK_SECRET_PATH",
        "ENCRYPTION_KEY",
        "NVIDIA_NIM_KEY",
        "NVIDIA_API_KEY",
        "NVCF_API_KEY",
        "SENTRY_DSN",
    ] {
        if let Ok(val) = std::env::var(key) {
            if !val.is_empty() {
                output = output.replace(&val, &format!("[REDACTED_{}]", key));
            }
        }
    }
    output
}
