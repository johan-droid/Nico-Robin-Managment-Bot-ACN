use std::collections::HashMap;
use std::time::Instant;

/// Result of a rate-limit check.
#[derive(Debug, PartialEq)]
#[allow(dead_code)]
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
#[allow(dead_code)]
pub struct RateLimiter {
    /// Per-user_id command timestamps for a specific chat.
    user_buckets: HashMap<i64, Vec<Instant>>,
    /// Global command timestamps for this chat.
    global_bucket: Vec<Instant>,
}

#[allow(dead_code)]
impl RateLimiter {
    pub fn new() -> Self {
        Self {
            user_buckets: HashMap::new(),
            global_bucket: Vec::new(),
        }
    }

    /// Checks and records a command invocation at both levels.
    /// Returns `Allowed` if within all limits, `Denied` otherwise.
    pub fn check(&mut self, user_id: i64) -> RateLimitResult {
        const COOLDOWN_SECS: u32 = 30;
        const GLOBAL_LIMIT: usize = 300;
        const USER_LIMIT: usize = 20;

        let now = Instant::now();
        let window = std::time::Duration::from_secs(COOLDOWN_SECS as u64);

        // --- Global level check ---
        self.global_bucket
            .retain(|ts| now.duration_since(*ts) < window);
        if self.global_bucket.len() >= GLOBAL_LIMIT {
            return RateLimitResult::Denied {
                retry_after_secs: COOLDOWN_SECS,
            };
        }
        self.global_bucket.push(now);

        // --- Per-user-per-group level check ---
        let timestamps = self.user_buckets.entry(user_id).or_default();
        timestamps.retain(|ts| now.duration_since(*ts) < window);

        if timestamps.len() >= USER_LIMIT {
            return RateLimitResult::Denied {
                retry_after_secs: COOLDOWN_SECS,
            };
        }
        timestamps.push(now);

        RateLimitResult::Allowed
    }
}

