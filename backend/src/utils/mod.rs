pub mod crash_reporter;
pub mod error;
pub mod logging;
pub mod sentry_scrubber;

/// Escapes characters that are special in Telegram MarkdownV2 format.
/// Must be applied to all user-generated content before sending with MarkdownV2 parse mode.
pub fn escape_md_v2(text: &str) -> String {
    let mut result = String::with_capacity(text.len() * 2);
    for c in text.chars() {
        match c {
            '_' | '*' | '[' | ']' | '(' | ')' | '~' | '`' | '>' | '<' | '#' | '+' | '-' | '='
            | '|' | '{' | '}' | '.' | '!' | '\\' => {
                result.push('\\');
                result.push(c);
            }
            _ => result.push(c),
        }
    }
    result
}

/// Escapes characters that are special in Telegram HTML parse mode.
pub fn escape_html(text: &str) -> String {
    text.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
}

pub fn spawn_task<F>(future: F)
where
    F: std::future::Future<Output = ()> + Send + 'static,
{
    tokio::spawn(future);
}
