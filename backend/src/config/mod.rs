use serde::{Deserialize, Deserializer};
use std::env;

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

#[derive(Deserialize, Debug, Clone)]
pub struct Settings {
    #[serde(rename = "bot_token")]
    pub bot_token: String,

    #[serde(rename = "bot_mode", default = "default_bot_mode")]
    pub bot_mode: String,

    #[serde(rename = "webhook_url", default)]
    pub webhook_url: String,

    #[serde(rename = "render_external_url", default)]
    pub render_external_url: String,

    #[serde(rename = "webhook_secret", default)]
    pub webhook_secret: String,

    #[serde(rename = "webhook_path", default = "default_webhook_path")]
    pub webhook_path: String,

    #[serde(rename = "webhook_path_token", default)]
    pub webhook_path_token: String,

    #[serde(rename = "webhook_require_secret_header", default = "default_true")]
    pub webhook_require_secret_header: bool,

    #[serde(rename = "webhook_drop_pending_updates", default = "default_true")]
    pub webhook_drop_pending_updates: bool,

    #[serde(rename = "port", default = "default_port")]
    pub port: u16,

    // WebSocket Configuration
    #[serde(rename = "websocket_enabled", default = "default_true")]
    pub websocket_enabled: bool,

    #[serde(rename = "websocket_port", default = "default_websocket_port")]
    pub websocket_port: u16,

    #[serde(rename = "websocket_cors_origin", default = "default_cors")]
    pub websocket_cors_origin: String,

    #[serde(rename = "websocket_ping_interval", default = "default_ping_interval")]
    pub websocket_ping_interval: u32,

    #[serde(rename = "websocket_ping_timeout", default = "default_ping_timeout")]
    pub websocket_ping_timeout: u32,

    // Real-time Events Configuration
    #[serde(rename = "realtime_events_enabled", default = "default_true")]
    pub realtime_events_enabled: bool,

    #[serde(rename = "event_batch_size", default = "default_batch_size")]
    pub event_batch_size: u32,

    #[serde(rename = "event_retention_hours", default = "default_retention_hours")]
    pub event_retention_hours: u32,

    // User/Group IDs configurations
    #[serde(rename = "sudo_users", default, deserialize_with = "deserialize_comma_separated_ints")]
    pub sudo_users: Vec<i64>,

    #[serde(rename = "captain_id", default)]
    pub captain_id: i64,

    #[serde(rename = "commander_ids", default, deserialize_with = "deserialize_comma_separated_ints")]
    pub commander_ids: Vec<i64>,

    #[serde(rename = "allowed_group_ids", default, deserialize_with = "deserialize_comma_separated_ints")]
    pub allowed_group_ids: Vec<i64>,

    #[serde(rename = "purge_channel_ids", default, deserialize_with = "deserialize_comma_separated_ints")]
    pub purge_channel_ids: Vec<i64>,

    // Security Configuration
    #[serde(rename = "metrics_api_key", default)]
    pub metrics_api_key: String,

    #[serde(rename = "data_encryption_key", default)]
    pub data_encryption_key: Option<String>,

    // Rate limiting settings
    #[serde(rename = "rate_limit_user", default = "default_rl_user")]
    pub rate_limit_user: u32,

    #[serde(rename = "rate_limit_group", default = "default_rl_group")]
    pub rate_limit_group: u32,

    #[serde(rename = "rate_limit_global", default = "default_rl_global")]
    pub rate_limit_global: u32,

    #[serde(rename = "rate_limit_cooldown", default = "default_rl_cooldown")]
    pub rate_limit_cooldown: u32,

    #[serde(rename = "rate_limit_ban_threshold", default = "default_rl_ban_threshold")]
    pub rate_limit_ban_threshold: u32,

    // Database configurations
    #[serde(rename = "db_pool_size", default = "default_db_pool")]
    pub db_pool_size: u32,

    #[serde(rename = "db_max_overflow", default = "default_db_overflow")]
    pub db_max_overflow: u32,

    #[serde(rename = "db_connect_timeout", default = "default_db_timeout")]
    pub db_connect_timeout: u32,

    #[serde(rename = "db_query_timeout", default = "default_db_query_timeout")]
    pub db_query_timeout: u32,

    #[serde(rename = "db_pool_recycle", default = "default_db_recycle")]
    pub db_pool_recycle: u32,

    #[serde(rename = "db_ssl_required", default)]
    pub db_ssl_required: bool,

    #[serde(rename = "database_url")]
    pub database_url: String,

    #[serde(rename = "redis_url", default = "default_redis_url")]
    pub redis_url: String,

    // Celery equivalent configurations
    #[serde(rename = "celery_broker_url", default)]
    pub celery_broker_url: String,

    #[serde(rename = "celery_result_backend", default)]
    pub celery_result_backend: String,

    #[serde(rename = "moderation_provider", default = "default_moderation_provider")]
    pub moderation_provider: String,

    #[serde(rename = "ai_moderation_enabled", default)]
    pub ai_moderation_enabled: bool,

    #[serde(rename = "ai_score_threshold", default = "default_ai_threshold")]
    pub ai_score_threshold: f32,

    #[serde(rename = "log_channel_id", default)]
    pub log_channel_id: Option<i64>,

    #[serde(rename = "bot_name", default = "default_bot_name")]
    pub bot_name: String,

    #[serde(rename = "default_locale", default = "default_locale")]
    pub default_locale: String,

    #[serde(rename = "default_prefix", default = "default_prefix")]
    pub default_prefix: String,

    #[serde(rename = "environment", default = "default_environment")]
    pub environment: String,

    #[serde(rename = "log_level", default = "default_log_level")]
    pub log_level: String,

    #[serde(rename = "auto_migrate_on_startup", default = "default_true")]
    pub auto_migrate_on_startup: bool,
}

fn default_bot_mode() -> String { "auto".to_string() }
fn default_webhook_path() -> String { "/telegram/webhook".to_string() }
fn default_true() -> bool { true }
fn default_port() -> u16 { 8000 }
fn default_websocket_port() -> u16 { 8001 }
fn default_cors() -> String { "*".to_string() }
fn default_ping_interval() -> u32 { 25 }
fn default_ping_timeout() -> u32 { 5 }
fn default_batch_size() -> u32 { 100 }
fn default_retention_hours() -> u32 { 24 }
fn default_rl_user() -> u32 { 20 }
fn default_rl_group() -> u32 { 60 }
fn default_rl_global() -> u32 { 300 }
fn default_rl_cooldown() -> u32 { 30 }
fn default_rl_ban_threshold() -> u32 { 5 }
fn default_db_pool() -> u32 { 10 }
fn default_db_overflow() -> u32 { 5 }
fn default_db_timeout() -> u32 { 30 }
fn default_db_query_timeout() -> u32 { 10 }
fn default_db_recycle() -> u32 { 1800 }
fn default_redis_url() -> String { "redis://localhost:6379/0".to_string() }
fn default_moderation_provider() -> String { "disabled".to_string() }
fn default_ai_threshold() -> f32 { 0.75 }
fn default_bot_name() -> String { "Nico Robin".to_string() }
fn default_locale() -> String { "en".to_string() }
fn default_prefix() -> String { "/".to_string() }
fn default_environment() -> String { "local".to_string() }
fn default_log_level() -> String { "INFO".to_string() }

impl Settings {
    pub fn load() -> Result<Self, envy::Error> {
        let _ = dotenvy::dotenv();
        envy::from_env::<Settings>()
    }

    pub fn database_url_clean(&self) -> String {
        let mut url = self.database_url.trim().to_string();
        if url.starts_with("postgres://") {
            url = url.replacen("postgres://", "postgresql://", 1);
        }
        url
    }
}
