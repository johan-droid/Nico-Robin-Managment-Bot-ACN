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

impl Default for Settings {
    fn default() -> Self {
        Self {
            bot_token: "".to_string(),
            log_channel_id: None,
            rate_limit_user: 20,
            rate_limit_global: 300,
            rate_limit_cooldown: 30,
            warn_threshold: 3,
        }
    }
}
