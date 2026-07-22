use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

use tokio::sync::RwLock;

use crate::config::Settings;

/// Result of a rate-limit check.
#[derive(Debug, PartialEq)]
pub enum RateLimitResult {
    /// Request is allowed.
    Allowed,
    /// Request is denied — user should wait.
    Denied { retry_after_secs: u32 },
}

/// Multi-level sliding-window rate limiter.
///
/// Tracks command timestamps at two levels:
/// 1. **Per-user-per-group**: prevents a single user from spamming commands in a group.
/// 2. **Global**: prevents distributed abuse across all groups.
pub struct RateLimiter {
    /// Per-(user_id, chat_id) command timestamps.
    user_buckets: RwLock<HashMap<(i64, i64), Vec<Instant>>>,
    /// Global command timestamps (all users, all chats).
    global_bucket: RwLock<Vec<Instant>>,
}

pub type SharedRateLimiter = Arc<RateLimiter>;

impl RateLimiter {
    pub fn new() -> Self {
        Self {
            user_buckets: RwLock::new(HashMap::new()),
            global_bucket: RwLock::new(Vec::new()),
        }
    }

    /// Checks and records a command invocation at both levels.
    /// Returns `Allowed` if within all limits, `Denied` otherwise.
    pub async fn check(&self, user_id: i64, chat_id: i64, settings: &Settings) -> RateLimitResult {
        let now = Instant::now();
        let window = std::time::Duration::from_secs(settings.rate_limit_cooldown as u64);

        // --- Global level check ---
        {
            let mut global = self.global_bucket.write().await;
            global.retain(|ts| now.duration_since(*ts) < window);
            if global.len() >= settings.rate_limit_global as usize {
                return RateLimitResult::Denied {
                    retry_after_secs: settings.rate_limit_cooldown,
                };
            }
            global.push(now);
        }

        // --- Per-user-per-group level check ---
        {
            let mut buckets = self.user_buckets.write().await;
            let timestamps = buckets.entry((user_id, chat_id)).or_default();
            timestamps.retain(|ts| now.duration_since(*ts) < window);

            if timestamps.len() >= settings.rate_limit_user as usize {
                return RateLimitResult::Denied {
                    retry_after_secs: settings.rate_limit_cooldown,
                };
            }
            timestamps.push(now);
        }

        RateLimitResult::Allowed
    }

    /// Periodically clean up stale entries to prevent memory leaks.
    /// Call from a background task every few minutes.
    pub async fn cleanup(&self, max_age_secs: u64) {
        let now = Instant::now();
        let max_age = std::time::Duration::from_secs(max_age_secs);

        {
            let mut buckets = self.user_buckets.write().await;
            buckets.retain(|_, timestamps| {
                timestamps.retain(|ts| now.duration_since(*ts) < max_age);
                !timestamps.is_empty()
            });
        }

        {
            let mut global = self.global_bucket.write().await;
            global.retain(|ts| now.duration_since(*ts) < max_age);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_settings(user_limit: u32, global_limit: u32, cooldown: u32) -> Settings {
        serde_json::from_value(serde_json::json!({
            "bot_token": "test:token",
            "database_url": "postgres://localhost/test",
            "rate_limit_user": user_limit,
            "rate_limit_global": global_limit,
            "rate_limit_cooldown": cooldown,
        }))
        .unwrap()
    }

    #[tokio::test]
    async fn test_allows_within_limit() {
        let rl = RateLimiter::new();
        let settings = test_settings(3, 100, 60);
        assert_eq!(rl.check(1, 1, &settings).await, RateLimitResult::Allowed);
        assert_eq!(rl.check(1, 1, &settings).await, RateLimitResult::Allowed);
        assert_eq!(rl.check(1, 1, &settings).await, RateLimitResult::Allowed);
    }

    #[tokio::test]
    async fn test_denies_over_user_limit() {
        let rl = RateLimiter::new();
        let settings = test_settings(2, 100, 60);
        assert_eq!(rl.check(1, 1, &settings).await, RateLimitResult::Allowed);
        assert_eq!(rl.check(1, 1, &settings).await, RateLimitResult::Allowed);
        assert!(matches!(
            rl.check(1, 1, &settings).await,
            RateLimitResult::Denied { .. }
        ));
    }

    #[tokio::test]
    async fn test_denies_over_global_limit() {
        let rl = RateLimiter::new();
        let settings = test_settings(100, 2, 60);
        assert_eq!(rl.check(1, 1, &settings).await, RateLimitResult::Allowed);
        assert_eq!(rl.check(2, 2, &settings).await, RateLimitResult::Allowed);
        assert!(matches!(
            rl.check(3, 3, &settings).await,
            RateLimitResult::Denied { .. }
        ));
    }

    #[tokio::test]
    async fn test_different_users_independent() {
        let rl = RateLimiter::new();
        let settings = test_settings(1, 100, 60);
        assert_eq!(rl.check(1, 1, &settings).await, RateLimitResult::Allowed);
        assert_eq!(rl.check(2, 1, &settings).await, RateLimitResult::Allowed);
    }
}
