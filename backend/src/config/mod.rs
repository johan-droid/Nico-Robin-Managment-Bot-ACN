use serde::Deserialize;
use std::sync::OnceLock;

#[derive(Clone, Debug, Deserialize)]
pub struct Settings {
    pub bot_token: String,
    pub encryption_key: String,
    pub log_channel_id: Option<i64>,
    pub rate_limit_user: u32,
    pub rate_limit_global: u32,
    pub rate_limit_cooldown: u32,
    pub warn_threshold: u32,
}

static GLOBAL_SETTINGS: OnceLock<Settings> = OnceLock::new();

impl Settings {
    pub fn from_env() -> Self {
        Self {
            bot_token: std::env::var("BOT_TOKEN").unwrap_or_default(),
            encryption_key: std::env::var("ENCRYPTION_KEY").unwrap_or_default(),
            log_channel_id: std::env::var("LOG_CHANNEL_ID")
                .ok()
                .and_then(|v| v.parse().ok()),
            rate_limit_user: std::env::var("RATE_LIMIT_USER")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(20),
            rate_limit_global: std::env::var("RATE_LIMIT_GLOBAL")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(300),
            rate_limit_cooldown: std::env::var("RATE_LIMIT_COOLDOWN")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(30),
            warn_threshold: std::env::var("WARN_THRESHOLD")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(3),
        }
    }

    /// Initialize the global singleton (call once at startup).
    pub fn init_global() -> &'static Self {
        GLOBAL_SETTINGS.get_or_init(Self::from_env)
    }

    /// Get the global singleton (panics if not initialized — but init_global is called at startup).
    pub fn global() -> &'static Settings {
        GLOBAL_SETTINGS
            .get()
            .expect("Settings not initialized. Call Settings::init_global() at startup.")
    }
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            bot_token: String::new(),
            encryption_key: String::new(),
            log_channel_id: None,
            rate_limit_user: 20,
            rate_limit_global: 300,
            rate_limit_cooldown: 30,
            warn_threshold: 3,
        }
    }
}
