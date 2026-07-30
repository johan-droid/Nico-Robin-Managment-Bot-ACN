use std::panic;
use std::fs;
use std::path::Path;
use chrono::Utc;
use futures_util::FutureExt;
use crate::utils::error::sanitize_secrets;

pub async fn catch_handler_panic<F, R>(
    trace_id: u64,
    fut: F,
) -> Result<R, String>
where
    F: std::future::Future<Output = Result<R, String>> + Send + 'static,
{
    let result = panic::AssertUnwindSafe(fut).catch_unwind().await;
    match result {
        Ok(res) => res,
        Err(err) => {
            let panic_msg = if let Some(s) = err.downcast_ref::<&str>() {
                *s
            } else if let Some(s) = err.downcast_ref::<String>() {
                s.as_str()
            } else {
                "Unknown panic"
            };

            report_crash(trace_id, panic_msg);
            Err(format!("Panic occurred: {}", panic_msg))
        }
    }
}

pub fn report_crash(trace_id: u64, panic_msg: &str) {
    let dir = Path::new("diagnostics/crashes");
    if let Err(e) = fs::create_dir_all(dir) {
        eprintln!("Failed to create diagnostics/crashes directory: {}", e);
        return;
    }

    let timestamp = Utc::now().to_rfc3339();
    let filename = format!("crash_{}_{}.md", Utc::now().format("%Y%m%d_%H%M%S"), trace_id);
    let filepath = dir.join(filename);

    let logs = crate::utils::logging::LOG_BUFFER.try_with(|buf| {
        buf.borrow().join("\n")
    }).unwrap_or_else(|_| "No trace logs recorded".to_string());

    let sanitized_msg = sanitize_secrets(panic_msg);
    let sanitized_logs = sanitize_secrets(&logs);

    let backtrace = std::backtrace::Backtrace::capture();
    let backtrace_str = format!("{:#?}", backtrace);
    let sanitized_backtrace = sanitize_secrets(&backtrace_str);

    let report = format!(
        "# Unhandled Crash Report\n\n\
         - **Timestamp**: {}\n\
         - **Trace ID**: {}\n\
         - **Component**: Webhook Handler\n\
         - **Operation**: Process Telegram Message\n\n\
         ## Panic Message\n\
         ```\n\
         {}\n\
         ```\n\n\
         ## Stack Backtrace\n\
         ```\n\
         {}\n\
         ```\n\n\
         ## Related Execution Logs\n\
         ```\n\
         {}\n\
         ```\n",
        timestamp, trace_id, sanitized_msg, sanitized_backtrace, sanitized_logs
    );

    if let Err(e) = fs::write(&filepath, report) {
        eprintln!("Failed to write crash report: {}", e);
    }

    sentry::configure_scope(|scope| {
        scope.set_tag("trace_id", trace_id.to_string());
        scope.set_tag("component", "Webhook Handler");
        scope.set_tag("operation", "Process Telegram Message");
        scope.set_extra("backtrace", serde_json::Value::String(sanitized_backtrace));
        scope.set_extra("logs", serde_json::Value::String(sanitized_logs));
    });
    sentry::capture_message(&format!("Crash: {}", sanitized_msg), sentry::Level::Fatal);
}
