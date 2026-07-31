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

/// Sliding-window rate limiter per chat.
///
/// Tracks command timestamps at two levels:
/// 1. **Per-user**: prevents a single user from spamming commands in this group.
/// 2. **Per-chat**: prevents group-wide command flooding.
#[allow(dead_code)]
pub struct RateLimiter {
    /// Per-user_id command timestamps for this chat.
    user_buckets: HashMap<i64, Vec<Instant>>,
    /// Aggregate command timestamps for this chat.
    global_bucket: Vec<Instant>,
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new()
    }
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
    /// Returns `Allowed` if within all limits, `Denied` otherwise with exact remaining retry seconds.
    pub fn check(&mut self, user_id: i64) -> RateLimitResult {
        const COOLDOWN_SECS: u32 = 30;
        const GLOBAL_LIMIT: usize = 300;
        const USER_LIMIT: usize = 20;

        let now = Instant::now();
        let window = std::time::Duration::from_secs(COOLDOWN_SECS as u64);

        let calc_retry_after = |timestamps: &[Instant]| -> u32 {
            if let Some(oldest) = timestamps.first() {
                let elapsed = now.duration_since(*oldest);
                if elapsed < window {
                    (window - elapsed).as_secs().max(1) as u32
                } else {
                    1
                }
            } else {
                COOLDOWN_SECS
            }
        };

        // --- Aggregate chat level check ---
        self.global_bucket
            .retain(|ts| now.duration_since(*ts) < window);
        if self.global_bucket.len() >= GLOBAL_LIMIT {
            return RateLimitResult::Denied {
                retry_after_secs: calc_retry_after(&self.global_bucket),
            };
        }

        // --- Per-user level check ---
        let timestamps = self.user_buckets.entry(user_id).or_default();
        timestamps.retain(|ts| now.duration_since(*ts) < window);

        if timestamps.len() >= USER_LIMIT {
            return RateLimitResult::Denied {
                retry_after_secs: calc_retry_after(timestamps),
            };
        }

        self.global_bucket.push(now);
        timestamps.push(now);

        RateLimitResult::Allowed
    }

    /// Periodically evicts stale timestamp buckets.
    pub fn cleanup_stale(&mut self, max_age: std::time::Duration) {
        let now = Instant::now();
        self.user_buckets.retain(|_, ts_vec| {
            ts_vec.retain(|ts| now.duration_since(*ts) < max_age);
            !ts_vec.is_empty()
        });
        self.global_bucket.retain(|ts| now.duration_since(*ts) < max_age);
    }
}

