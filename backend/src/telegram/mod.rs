pub mod native_api;
pub use crate::telegram::native_api as api;

pub mod update;

/// Shared ParseMode enum used by the API implementation.
pub enum ParseMode {
    MarkdownV2,
    Html,
}
