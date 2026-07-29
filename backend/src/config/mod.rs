use serde::Deserialize;

#[derive(Clone, Debug, Deserialize)]
pub struct Settings {
    pub bot_token: String,
    pub log_channel_id: Option<i64>,
    pub rate_limit_user: u32,
    pub rate_limit_global: u32,
    pub rate_limit_cooldown: u32,
    pub warn_threshold: u32,
}

impl Settings {
    pub fn from_env() -> Self {
        #[cfg(not(target_arch = "wasm32"))]
        {
            Self {
                bot_token: std::env::var("BOT_TOKEN").unwrap_or_default(),
                log_channel_id: std::env::var("LOG_CHANNEL_ID").ok().and_then(|v| v.parse().ok()),
                rate_limit_user: std::env::var("RATE_LIMIT_USER").ok().and_then(|v| v.parse().ok()).unwrap_or(20),
                rate_limit_global: std::env::var("RATE_LIMIT_GLOBAL").ok().and_then(|v| v.parse().ok()).unwrap_or(300),
                rate_limit_cooldown: std::env::var("RATE_LIMIT_COOLDOWN").ok().and_then(|v| v.parse().ok()).unwrap_or(30),
                warn_threshold: std::env::var("WARN_THRESHOLD").ok().and_then(|v| v.parse().ok()).unwrap_or(3),
            }
        }
        #[cfg(target_arch = "wasm32")]
        {
            Self::default()
        }
    }

    #[cfg(target_arch = "wasm32")]
    pub fn from_worker_env(env: &worker::Env) -> Self {
        Self {
            bot_token: crate::utils::get_env_val(env, "BOT_TOKEN").unwrap_or_default(),
            log_channel_id: crate::utils::get_env_val(env, "LOG_CHANNEL_ID").ok().and_then(|v| v.parse().ok()),
            rate_limit_user: crate::utils::get_env_val(env, "RATE_LIMIT_USER").ok().and_then(|v| v.parse().ok()).unwrap_or(20),
            rate_limit_global: crate::utils::get_env_val(env, "RATE_LIMIT_GLOBAL").ok().and_then(|v| v.parse().ok()).unwrap_or(300),
            rate_limit_cooldown: crate::utils::get_env_val(env, "RATE_LIMIT_COOLDOWN").ok().and_then(|v| v.parse().ok()).unwrap_or(30),
            warn_threshold: crate::utils::get_env_val(env, "WARN_THRESHOLD").ok().and_then(|v| v.parse().ok()).unwrap_or(3),
        }
    }
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            bot_token: String::new(),
            log_channel_id: None,
            rate_limit_user: 20,
            rate_limit_global: 300,
            rate_limit_cooldown: 30,
            warn_threshold: 3,
        }
    }
}