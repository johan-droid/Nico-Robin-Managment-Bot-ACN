pub mod native_api;
pub use crate::telegram::native_api as api;

pub mod update;

use std::sync::RwLock;

static BOT_USERNAME: std::sync::LazyLock<RwLock<Option<String>>> =
    std::sync::LazyLock::new(|| RwLock::new(None));

pub fn set_bot_username(username: &str) {
    let clean = username.trim().trim_start_matches('@').to_string();
    if let Ok(mut guard) = BOT_USERNAME.write() {
        *guard = Some(clean);
    }
}

pub fn get_bot_username() -> Option<String> {
    if let Ok(guard) = BOT_USERNAME.read() {
        guard.clone()
    } else {
        None
    }
}

/// Shared ParseMode enum used by the API implementation.
#[derive(Clone, Copy)]
pub enum ParseMode {
    MarkdownV2,
    Html,
}
