use tracing::Level;
use tracing_subscriber::fmt;
use tracing_subscriber::prelude::*;
use tracing_subscriber::EnvFilter;

pub fn configure_logging(log_level: &str, environment: &str) {
    let parsed_level = match log_level.to_uppercase().as_str() {
        "DEBUG" => Level::DEBUG,
        "WARNING" | "WARN" => Level::WARN,
        "ERROR" => Level::ERROR,
        "CRITICAL" => Level::ERROR,
        _ => Level::INFO,
    };

    let filter = EnvFilter::from_default_env()
        .add_directive(parsed_level.into())
        .add_directive("hyper=info".parse().unwrap())
        .add_directive("sqlx=info".parse().unwrap())
        .add_directive("teloxide=info".parse().unwrap());

    if environment.to_lowercase() == "production" {
        tracing_subscriber::registry()
            .with(filter)
            .with(fmt::layer().json().with_current_span(true))
            .init();
    } else {
        tracing_subscriber::registry()
            .with(filter)
            .with(fmt::layer().pretty())
            .init();
    }

    tracing::info!(
        log_level = log_level,
        environment = environment,
        "logging_initialized"
    );
}
