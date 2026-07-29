#[cfg(target_arch = "wasm32")]
pub mod api;

#[cfg(not(target_arch = "wasm32"))]
pub mod native_api;

#[cfg(not(target_arch = "wasm32"))]
pub use crate::telegram::native_api as api;

pub mod update;

/// Shared ParseMode enum used by both wasm32 and native API implementations.
pub enum ParseMode {
    MarkdownV2,
}