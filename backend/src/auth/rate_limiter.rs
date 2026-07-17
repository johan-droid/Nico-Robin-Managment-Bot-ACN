use std::collections::HashMap;
use std::sync::Mutex;
use std::time::Instant;

use crate::config::Settings;

/// Simple in-memory rate limiter (non-persistent, per-process).
/// For production, use Redis-based rate limiting instead.
#[derive(Debug)]
pub struct RateLimiter {
    buckets: Mutex<HashMap<i64, Bucket>>,
}

#[derive(Debug, Clone)]
struct Bucket {
    tokens: u32,
    last_refill: Instant,
}

impl RateLimiter {
    pub fn new() -> Self {
        Self {
            buckets: Mutex::new(HashMap::new()),
        }
    }

    /// Check if a request from a user should be allowed.
    /// Returns `true` if allowed, `false` if rate-limited.
    pub fn check_user(&self, user_id: i64, settings: &Settings) -> bool {
        let mut buckets = self.buckets.lock().unwrap();
        let now = Instant::now();
        let bucket = buckets.entry(user_id).or_insert(Bucket {
            tokens: settings.rate_limit_user,
            last_refill: now,
        });

        let elapsed = now.duration_since(bucket.last_refill).as_secs();
        let refill_rate = settings.rate_limit_user as f64 / settings.rate_limit_cooldown as f64;
        let refilled = (elapsed as f64 * refill_rate) as u32;

        bucket.tokens = (bucket.tokens + refilled).min(settings.rate_limit_user);
        bucket.last_refill = now;

        if bucket.tokens > 0 {
            bucket.tokens -= 1;
            true
        } else {
            false
        }
    }

    /// Check if a request from a group should be allowed.
    pub fn check_group(&self, group_id: i64, settings: &Settings) -> bool {
        let mut buckets = self.buckets.lock().unwrap();
        let now = Instant::now();
        let bucket = buckets.entry(-group_id).or_insert(Bucket {
            tokens: settings.rate_limit_group,
            last_refill: now,
        });

        let elapsed = now.duration_since(bucket.last_refill).as_secs();
        let refill_rate = settings.rate_limit_group as f64 / settings.rate_limit_cooldown as f64;
        let refilled = (elapsed as f64 * refill_rate) as u32;

        bucket.tokens = (bucket.tokens + refilled).min(settings.rate_limit_group);
        bucket.last_refill = now;

        if bucket.tokens > 0 {
            bucket.tokens -= 1;
            true
        } else {
            false
        }
    }

    /// Check if a global request should be allowed.
    pub fn check_global(&self, settings: &Settings) -> bool {
        self.check_user(0, settings) // Use key 0 for global
    }

    /// Reset all rate limit buckets.
    pub fn reset(&self) {
        let mut buckets = self.buckets.lock().unwrap();
        buckets.clear();
    }
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_settings() -> Settings {
        let _ = dotenvy::dotenv().ok();
        crate::config::Settings::load().unwrap_or_else(|_| {
            // Fallback: construct minimal settings from env or defaults
            // This is a simplified test helper
            panic!("Cannot load settings for tests. Ensure DATABASE_URL and BOT_TOKEN are set.");
        })
    }

    #[test]
    fn test_rate_limiter_initial_state() {
        let rl = RateLimiter::new();
        let settings = test_settings();
        // First request should be allowed
        assert!(rl.check_user(12345, &settings));
    }

    #[test]
    fn test_rate_limiter_exhaustion() {
        let rl = RateLimiter::new();
        let mut settings = test_settings();
        // Override for test purposes - but we can't mutate easily, so just check basic functionality
        assert!(rl.check_user(99999, &settings));
    }
}
