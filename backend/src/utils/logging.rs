use std::cell::RefCell;
use tracing::Subscriber;
use tracing_subscriber::layer::Context;
use tracing_subscriber::{fmt, prelude::*, Layer};

tokio::task_local! {
    pub static LOG_BUFFER: RefCell<Vec<String>>;
}

pub struct TaskLocalLogLayer;

impl<S> Layer<S> for TaskLocalLogLayer
where
    S: Subscriber,
{
    fn on_event(
        &self,
        event: &tracing::Event<'_>,
        _ctx: Context<'_, S>,
    ) {
        let _ = LOG_BUFFER.try_with(|buf| {
            let metadata = event.metadata();
            let mut msg = format!("[{}] ", metadata.level());
            
            struct VisitMessage<'a>(&'a mut String);
            impl<'a> tracing::field::Visit for VisitMessage<'a> {
                fn record_debug(&mut self, field: &tracing::field::Field, value: &dyn std::fmt::Debug) {
                    if field.name() == "message" {
                        use std::fmt::Write;
                        let _ = write!(self.0, "{:?}", value);
                    } else {
                        use std::fmt::Write;
                        let _ = write!(self.0, " {}={:?}", field.name(), value);
                    }
                }
                fn record_str(&mut self, field: &tracing::field::Field, value: &str) {
                    if field.name() == "message" {
                        self.0.push_str(value);
                    } else {
                        self.0.push_str(&format!(" {}={}", field.name(), value));
                    }
                }
            }
            
            event.record(&mut VisitMessage(&mut msg));
            buf.borrow_mut().push(msg);
        });
    }
}

pub fn init() {
    let env_filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .or_else(|_| {
            let level = std::env::var("LOG_LEVEL").unwrap_or_else(|_| "INFO".to_string());
            tracing_subscriber::EnvFilter::try_new(format!(
                "{level},h2=warn,hyper=warn,reqwest=warn,tokio_postgres=warn,rustls=warn"
            ))
        })
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info"));

    let fmt_layer = fmt::layer()
        .with_target(false)
        .with_thread_ids(false)
        .with_thread_names(false);

    let _ = tracing_subscriber::registry()
        .with(env_filter)
        .with(fmt_layer)
        .with(TaskLocalLogLayer)
        .try_init();
}
