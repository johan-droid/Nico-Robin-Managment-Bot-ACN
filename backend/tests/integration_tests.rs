use std::fs;
use std::path::Path;
use nico_robin_bot::utils::error::{BotError, sanitize_secrets, report_failure};
use nico_robin_bot::utils::crash_reporter::catch_handler_panic;
use nico_robin_bot::utils::escape_md_v2;

#[test]
fn test_escape_md_v2() {
    let raw = "hello_world.md! [test]";
    let escaped = escape_md_v2(raw);
    assert_eq!(escaped, "hello\\_world\\.md\\! \\[test\\]");
}

#[test]
fn test_sanitize_secrets_and_sentry_scrubber() {
    std::env::set_var("BOT_TOKEN", "123456:secrettokenvalue");
    std::env::set_var("DATABASE_URL", "postgresql://robin:password@localhost/robin_db");

    let raw_log = "Error connecting with token 123456:secrettokenvalue or url postgresql://robin:password@localhost/robin_db";
    let sanitized = sanitize_secrets(raw_log);

    assert!(sanitized.contains("[REDACTED_BOT_TOKEN]"));
    assert!(sanitized.contains("[REDACTED_DATABASE_URL]"));
    assert!(!sanitized.contains("123456:secrettokenvalue"));
    assert!(!sanitized.contains("password@localhost"));

    // Now test Sentry Scrubber sequentially to avoid race condition
    use nico_robin_bot::utils::sentry_scrubber::sentry_before_send;

    let mut event = sentry::protocol::Event::new();
    event.message = Some("Failed using BOT_TOKEN: 123456:secrettokenvalue".to_string());
    
    let breadcrumb = sentry::protocol::Breadcrumb {
        message: Some("Logged in with 123456:secrettokenvalue".to_string()),
        ..Default::default()
    };
    event.breadcrumbs.values.push(breadcrumb);
    
    let sanitized_event = sentry_before_send(event).unwrap();
    let sanitized_msg = sanitized_event.message.unwrap();
    let sanitized_breadcrumb = sanitized_event.breadcrumbs.values[0].message.as_ref().unwrap();
    
    assert!(sanitized_msg.contains("[REDACTED_BOT_TOKEN]"));
    assert!(!sanitized_msg.contains("123456:secrettokenvalue"));
    
    assert!(sanitized_breadcrumb.contains("[REDACTED_BOT_TOKEN]"));
    assert!(!sanitized_breadcrumb.contains("123456:secrettokenvalue"));
}

#[test]
fn test_report_failure() {
    let trace_id = 999999;
    let err = BotError::ValidationError("Testing failure reporting".to_string());
    
    // Clear out old test reports if any
    let _ = fs::remove_dir_all("diagnostics/failures");

    // Report the failure
    report_failure(&err, trace_id, "Test Component", "Test Operation");

    let dir = Path::new("diagnostics/failures");
    assert!(dir.exists());

    let mut found = false;
    for entry in fs::read_dir(dir).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();
        if path.is_file() && path.to_string_lossy().contains(&trace_id.to_string()) {
            let content = fs::read_to_string(path).unwrap();
            assert!(content.contains("# Failure Report"));
            assert!(content.contains("Test Component"));
            assert!(content.contains("Test Operation"));
            assert!(content.contains("Testing failure reporting"));
            found = true;
        }
    }
    assert!(found, "Failure report file was not generated");
}

#[tokio::test]
async fn test_catch_handler_panic() {
    let trace_id = 888888;
    
    // Clear out old test crash reports if any
    let _ = fs::remove_dir_all("diagnostics/crashes");

    let fut = async {
        if true {
            panic!("Test panic event");
        }
        Ok(())
    };

    let result: Result<(), String> = catch_handler_panic(trace_id, fut).await;
    assert!(result.is_err());
    assert!(result.unwrap_err().contains("Test panic event"));

    let dir = Path::new("diagnostics/crashes");
    assert!(dir.exists());

    let mut found = false;
    for entry in fs::read_dir(dir).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();
        if path.is_file() && path.to_string_lossy().contains(&trace_id.to_string()) {
            let content = fs::read_to_string(path).unwrap();
            assert!(content.contains("# Unhandled Crash Report"));
            assert!(content.contains("Test panic event"));
            assert!(content.contains("Stack Backtrace"));
            found = true;
        }
    }
    assert!(found, "Crash report file was not generated");
}
