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
    pub nvidia_nim_key: String,
    pub nvidia_nim_url: String,
    pub nvidia_nim_model: String,
    pub nvidia_nim_timeout: u64,
    pub nvidia_nim_rpm: u32,
    pub quiz_timeout_secs: u64,
    pub persist_message_history: bool,
    pub enable_command_logging: bool,
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
            nvidia_nim_key: std::env::var("NVIDIA_NIM_KEY")
                .or_else(|_| std::env::var("NVIDIA_API_KEY"))
                .or_else(|_| std::env::var("NVCF_API_KEY"))
                .unwrap_or_default(),
            nvidia_nim_url: std::env::var("NVIDIA_NIM_URL")
                .unwrap_or_else(|_| "https://integrate.api.nvidia.com/v1".to_string()),
            nvidia_nim_model: std::env::var("NVIDIA_NIM_MODEL")
                .unwrap_or_else(|_| "meta/llama-3.3-70b-instruct".to_string()),
            nvidia_nim_timeout: std::env::var("NVIDIA_NIM_TIMEOUT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(30),
            nvidia_nim_rpm: std::env::var("NVIDIA_NIM_RPM")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(40),
            quiz_timeout_secs: std::env::var("QUIZ_TIMEOUT_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(30),
            persist_message_history: std::env::var("PERSIST_MESSAGE_HISTORY")
                .ok()
                .and_then(|v| v.parse::<bool>().ok())
                .unwrap_or(false),
            enable_command_logging: std::env::var("ENABLE_COMMAND_LOGGING")
                .ok()
                .and_then(|v| v.parse::<bool>().ok())
                .unwrap_or(false),
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
            nvidia_nim_key: String::new(),
            nvidia_nim_url: "https://integrate.api.nvidia.com/v1".to_string(),
            nvidia_nim_model: "meta/llama-3.3-70b-instruct".to_string(),
            nvidia_nim_timeout: 30,
            nvidia_nim_rpm: 40,
            quiz_timeout_secs: 30,
            persist_message_history: false,
            enable_command_logging: false,
        }
    }
}
