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

/// Whole-word substring match. Returns true only if `needle` appears in
/// `haystack` bounded by non-word characters on both sides (or edges), so a
/// trigger like "is" or "tip" does not fire inside larger words.
pub fn contains_word(haystack: &str, needle: &str) -> bool {
    if needle.is_empty() {
        return false;
    }
    let bytes = haystack.as_bytes();
    let needle_len = needle.len();
    for idx in haystack.match_indices(needle).map(|(i, _)| i) {
        let before_ok =
            idx == 0 || !bytes[idx - 1].is_ascii_alphanumeric() && bytes[idx - 1] < 128;
        let after = idx + needle_len;
        let after_ok =
            after >= bytes.len() || !bytes[after].is_ascii_alphanumeric() && bytes[after] < 128;
        if before_ok && after_ok {
            return true;
        }
    }
    false
}

pub fn spawn_task<F>(future: F)
where
    F: std::future::Future<Output = ()> + Send + 'static,
{
    tokio::spawn(future);
}
