use std::collections::HashMap;
use std::sync::RwLock;
use std::time::{Duration, Instant};

struct CacheEntry {
    enabled: bool,
    expires_at: Instant,
}

static FEATURE_CACHE: std::sync::LazyLock<RwLock<HashMap<(i64, String), CacheEntry>>> =
    std::sync::LazyLock::new(|| RwLock::new(HashMap::with_capacity(128)));

const CACHE_TTL_SECS: u64 = 600;

pub fn get_cached(group_id: i64, feature: &str) -> Option<bool> {
    let cache = FEATURE_CACHE.read().ok()?;
    let key = (group_id, feature.to_string());
    let entry = cache.get(&key)?;
    if entry.expires_at > Instant::now() {
        Some(entry.enabled)
    } else {
        None
    }
}

pub fn set_cached(group_id: i64, feature: &str, enabled: bool) {
    if let Ok(mut cache) = FEATURE_CACHE.write() {
        let key = (group_id, feature.to_string());
        cache.insert(
            key,
            CacheEntry {
                enabled,
                expires_at: Instant::now() + Duration::from_secs(CACHE_TTL_SECS),
            },
        );
    }
}

pub fn invalidate_group(group_id: i64) {
    if let Ok(mut cache) = FEATURE_CACHE.write() {
        cache.retain(|(gid, _), _| *gid != group_id);
    }
}
