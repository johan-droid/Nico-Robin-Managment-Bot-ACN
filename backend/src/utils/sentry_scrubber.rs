#[cfg(not(target_arch = "wasm32"))]
pub fn sentry_before_send(mut event: sentry::protocol::Event<'static>) -> Option<sentry::protocol::Event<'static>> {
    use crate::utils::error::sanitize_secrets;

    // Sanitize event message
    if let Some(ref mut msg) = event.message {
        *msg = sanitize_secrets(msg);
    }

    // Sanitize exception messages
    for exception in event.exception.iter_mut() {
        if let Some(ref mut val) = exception.value {
            *val = sanitize_secrets(val);
        }
    }

    // Sanitize extra metadata values
    for val in event.extra.values_mut() {
        if let Some(s) = val.as_str() {
            *val = serde_json::json!(sanitize_secrets(s));
        }
    }

    // Sanitize breadcrumbs
    for breadcrumb in event.breadcrumbs.iter_mut() {
        if let Some(ref mut message) = breadcrumb.message {
            *message = sanitize_secrets(message);
        }
        for val in breadcrumb.data.values_mut() {
            if let Some(s) = val.as_str() {
                *val = serde_json::json!(sanitize_secrets(s));
            }
        }
    }

    Some(event)
}
