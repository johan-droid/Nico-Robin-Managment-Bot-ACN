use serde::{Deserialize, Deserializer};

fn deserialize_comma_separated_ints<'de, D>(deserializer: D) -> Result<Vec<i64>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: String = Deserialize::deserialize(deserializer)?;
    if s.is_empty() {
        return Ok(Vec::new());
    }
    s.split(',')
        .map(|part| part.trim().parse::<i64>().map_err(serde::de::Error::custom))
        .collect()
}

mod defaults {
    pub fn bot_mode() -> String {
        "polling".to_string()
    }
    pub fn true_val() -> bool {
        true
    }
    pub fn port() -> u16 {
        8000
    }
    pub fn db_pool() -> u32 {
        10
    }
    pub fn db_overflow() -> u32 {
        5
    }
    pub fn db_timeout() -> u32 {
        30
    }
    pub fn db_query_timeout() -> u32 {
        10
    }
    pub fn db_recycle() -> u32 {
        1800
    }
    pub fn rl_user() -> u32 {
        20
    }
    pub fn rl_group() -> u32 {
        60
    }
    pub fn rl_global() -> u32 {
        300
    }
    pub fn rl_cooldown() -> u32 {
        30
    }
    pub fn rl_ban_threshold() -> u32 {
        5
    }
    pub fn bot_name() -> String {
        "Nico Robin".to_string()
    }
    pub fn locale() -> String {
        "en".to_string()
    }
    pub fn prefix() -> String {
        "/".to_string()
    }
    pub fn environment() -> String {
        "local".to_string()
    }
    pub fn log_level() -> String {
        "INFO".to_string()
    }
    pub fn moderation_provider() -> String {
        "disabled".to_string()
    }
    pub fn ai_threshold() -> f32 {
        0.75
    }
    pub fn warn_threshold() -> u32 {
        3
    }
}

#[derive(Deserialize, Debug, Clone)]
#[allow(dead_code)]
pub struct Settings {
    #[serde(rename = "bot_token")]
    pub bot_token: String,

    #[serde(rename = "bot_mode", default = "defaults::bot_mode")]
    pub bot_mode: String,

    #[serde(rename = "bot_name", default = "defaults::bot_name")]
    pub bot_name: String,

    #[serde(rename = "default_locale", default = "defaults::locale")]
    pub default_locale: String,

    #[serde(rename = "default_prefix", default = "defaults::prefix")]
    pub default_prefix: String,

    #[serde(rename = "port", default = "defaults::port")]
    pub port: u16,

    #[serde(rename = "environment", default = "defaults::environment")]
    pub environment: String,

    #[serde(rename = "log_level", default = "defaults::log_level")]
    pub log_level: String,

    // User/Group IDs
    #[serde(
        rename = "allowed_group_ids",
        default,
        deserialize_with = "deserialize_comma_separated_ints"
    )]
    pub allowed_group_ids: Vec<i64>,

    // Rate limiting
    #[serde(rename = "rate_limit_user", default = "defaults::rl_user")]
    pub rate_limit_user: u32,

    #[serde(rename = "rate_limit_group", default = "defaults::rl_group")]
    pub rate_limit_group: u32,

    #[serde(rename = "rate_limit_global", default = "defaults::rl_global")]
    pub rate_limit_global: u32,

    #[serde(rename = "rate_limit_cooldown", default = "defaults::rl_cooldown")]
    pub rate_limit_cooldown: u32,

    #[serde(
        rename = "rate_limit_ban_threshold",
        default = "defaults::rl_ban_threshold"
    )]
    pub rate_limit_ban_threshold: u32,

    // Database
    #[serde(rename = "db_pool_size", default = "defaults::db_pool")]
    pub db_pool_size: u32,

    #[serde(rename = "db_max_overflow", default = "defaults::db_overflow")]
    pub db_max_overflow: u32,

    #[serde(rename = "db_connect_timeout", default = "defaults::db_timeout")]
    pub db_connect_timeout: u32,

    #[serde(rename = "db_query_timeout", default = "defaults::db_query_timeout")]
    pub db_query_timeout: u32,

    #[serde(rename = "db_pool_recycle", default = "defaults::db_recycle")]
    pub db_pool_recycle: u32,

    #[serde(rename = "db_ssl_required", default)]
    pub db_ssl_required: bool,

    #[serde(rename = "database_url")]
    pub database_url: String,

    // Moderation
    #[serde(
        rename = "moderation_provider",
        default = "defaults::moderation_provider"
    )]
    pub moderation_provider: String,

    #[serde(rename = "ai_moderation_enabled", default)]
    pub ai_moderation_enabled: bool,

    #[serde(rename = "ai_score_threshold", default = "defaults::ai_threshold")]
    pub ai_score_threshold: f32,

    #[serde(rename = "log_channel_id", default)]
    pub log_channel_id: Option<i64>,

    #[serde(rename = "auto_migrate_on_startup", default = "defaults::true_val")]
    pub auto_migrate_on_startup: bool,

    #[serde(rename = "warn_threshold", default = "defaults::warn_threshold")]
    pub warn_threshold: u32,
}

impl Settings {
    pub fn load() -> Result<Self, envy::Error> {
        let _ = dotenvy::dotenv();
        let settings = envy::from_env::<Settings>()?;
        settings.validate()?;
        Ok(settings)
    }

    fn validate(&self) -> Result<(), envy::Error> {
        if self.bot_token.is_empty() {
            return Err(envy::Error::Custom(
                "BOT_TOKEN is required. Set it in your environment or .env file. On Render, ensure it is set in the dashboard (sync: false requires manual entry).".to_string()
            ));
        }
        if self.database_url.is_empty() {
            return Err(envy::Error::Custom(
                "DATABASE_URL is required. Set it in your environment or .env file.".to_string(),
            ));
        }
        if !self.database_url.starts_with("postgresql://")
            && !self.database_url.starts_with("postgres://")
        {
            return Err(envy::Error::Custom(format!(
                "DATABASE_URL must start with postgresql:// or postgres://. Got: {}",
                if self.database_url.len() > 40 {
                    format!("{}...", &self.database_url[..40])
                } else {
                    self.database_url.clone()
                }
            )));
        }
        Ok(())
    }

    pub fn database_url_clean(&self) -> String {
        let mut url = self.database_url.trim().to_string();
        if url.starts_with("postgres://") {
            url = url.replacen("postgres://", "postgresql://", 1);
        }
        if self.db_ssl_required && !url.contains("sslmode=") {
            if url.contains('?') {
                url.push_str("&sslmode=require");
            } else {
                url.push_str("?sslmode=require");
            }
        }
        url
    }
}
