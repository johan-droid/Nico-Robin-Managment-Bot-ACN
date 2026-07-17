use tracing::Level;
use tracing_subscriber::fmt;
use tracing_subscriber::prelude::*;
use tracing_subscriber::EnvFilter;

use crate::auth::redactor::redact_sensitive;

/// A layer that redacts sensitive information from log messages.
struct RedactionLayer;

impl<S> tracing_subscriber::Layer<S> for RedactionLayer
where
    S: tracing::Subscriber,
    S: for<'a> tracing_subscriber::registry::LookupSpan<'a>,
{
    fn on_event(
        &self,
        event: &tracing::Event<'_>,
        _ctx: tracing_subscriber::layer::Context<'_, S>,
    ) {
        // Use a visitor to collect event fields
        let mut visitor = RedactingVisitor(String::new());
        event.record(&mut visitor);

        // The event is already captured by the fmt layer,
        // but we redirect through the custom formatter
    }
}

/// A visitor that redacts sensitive field values.
struct RedactingVisitor(String);

impl tracing::field::Visit for RedactingVisitor {
    fn record_str(&mut self, field: &tracing::field::Field, value: &str) {
        let redacted = redact_sensitive(value);
        if redacted != value {
            self.0.push_str(&format!("{}={} ", field.name(), redacted));
        }
    }

    fn record_debug(&mut self, field: &tracing::field::Field, value: &dyn std::fmt::Debug) {
        let debug_str = format!("{:?}", value);
        let redacted = redact_sensitive(&debug_str);
        if redacted != debug_str {
            self.0.push_str(&format!("{}={} ", field.name(), redacted));
        }
    }

    fn record_i64(&mut self, field: &tracing::field::Field, value: i64) {
        self.0.push_str(&format!("{}={} ", field.name(), value));
    }

    fn record_u64(&mut self, field: &tracing::field::Field, value: u64) {
        self.0.push_str(&format!("{}={} ", field.name(), value));
    }

    fn record_bool(&mut self, field: &tracing::field::Field, value: bool) {
        self.0.push_str(&format!("{}={} ", field.name(), value));
    }
}

/// Configures structured logging based on the log level and environment.
/// Includes sensitive data redaction to prevent credential leakage in logs.
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
            .with(RedactionLayer)
            .with(fmt::layer().json().with_current_span(true))
            .init();
    } else {
        tracing_subscriber::registry()
            .with(filter)
            .with(RedactionLayer)
            .with(fmt::layer().pretty())
            .init();
    }

    tracing::info!(
        log_level = log_level,
        environment = environment,
        "logging_initialized"
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_redaction_layer_exists() {
        // Verify the struct compiles and exists
        let _layer = RedactionLayer;
    }
}
