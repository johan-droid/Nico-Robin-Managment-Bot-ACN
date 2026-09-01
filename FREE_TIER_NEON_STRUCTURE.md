# Neon Free Tier & Heroku Basic Dyno Optimization Architecture

## Executive Summary
This document defines the exact architectural layout and data flow rules for running the **Nico Robin Management Bot** on:
1. **Neon Free Tier Database**: 100 compute hours/month limit, 5-minute auto-suspend when idle.
2. **Heroku Basic Dyno**: 512 MB RAM limit, 1 vCPU container.

---

## 1. Neon Compute Hours Optimization (Zero-Waste DB Access)

Neon measures compute usage when the database instance is active. If no queries hit the database for **5 consecutive minutes**, Neon automatically scales to 0 (auto-suspends), consuming zero compute hours.

### A. Message History & Quoting (`/q`)
- **Problem**: In default setup, every single message received in Telegram triggers an `INSERT INTO message_history`. In active groups, this keeps Neon active 24/7 (744 hrs/month), exhausting the free tier in < 4 days.
- **Solution**:
  - `PERSIST_MESSAGE_HISTORY=false` (default).
  - All quote history is stored in an in-memory `MESSAGE_HISTORY` ring buffer (last 150 messages per chat) in RAM.
  - Zero SQL `INSERT`s are issued for regular chat messages.

### B. In-Memory Caching & TTL Extension
- **Filter Cache**: TTL extended from 30s to **600s (10 mins)**.
- **Swear Cache**: TTL extended from 60s to **600s (10 mins)**.
- **Feature Cache**: TTL extended from 30s to **600s (10 mins)**.
- **Instant Invalidation**: Admin commands (`/filter`, `/unfilter`, `/addswear`, `/delswear`, `/enable`, `/disable`) immediately call `invalidate_chat_caches(chat_id)` to drop the RAM cache for that chat, guaranteeing immediate updates without DB polling.

### C. Username & User Profile Write Guarding
- `USERNAME_CACHE_WRITE_GUARD`: Minimum DB write interval per user set to **3600 seconds (1 hour)**.
- Repeated messages from the same user within 1 hour use cached in-memory structures without issuing `INSERT INTO username_cache ... ON CONFLICT DO UPDATE` queries.

### D. Audit & Command Logging Bypass
- `ENABLE_COMMAND_LOGGING=false` (default).
- Command executions skip `INSERT INTO command_history`, saving write IOPS and compute awake time.

### E. Connection Pooling Strategy
- `DB_POOL_SIZE=5` (default).
- Keeping connection pools small ensures `deadpool-postgres` does not keep unnecessary idle connections open that prevent Neon from scaling to 0.

---

## 2. Heroku Basic Dyno Optimization (512 MB RAM Cap)

Heroku Eco/Basic Dynos trigger `R14` (Memory quota exceeded) errors if RSS exceeds 512 MB.

### A. Memory Bounding
- `HISTORY_MAX_PER_CHAT`: Bounded to 150 text messages per chat (sufficient for 10-message quotes).
- `MAX_AVATAR_CACHE_ENTRIES`: Bounded to 200 user profile images max with TTL eviction (`AVATAR_CACHE_TTL = 1 hr`).

### B. Binary Optimization
Cargo release profile in `Cargo.toml`:
```toml
[profile.release]
opt-level = "z"     # Optimize for minimum binary size
lto = true          # Link-Time Optimization
codegen-units = 1   # Maximum codegen optimization
strip = true        # Strip symbols from binary
```

---

## 3. Data Flow Matrix

| Feature / Action | Primary Store | DB Query Frequency | Cache TTL / Eviction | Memory Impact |
|---|---|---|---|---|
| `/q` (Quote lookup) | RAM (`MESSAGE_HISTORY`) | 0 (when `PERSIST_MESSAGE_HISTORY=false`) | 150 msgs / chat | ~20 KB / chat |
| Swear Filtering | RAM (`SWEAR_CACHE`) | 1 read per 10 mins / chat | 600s (instant invalidation on edit) | < 5 KB / chat |
| Filter Matching | RAM (`FILTER_CACHE`) | 1 read per 10 mins / chat | 600s (instant invalidation on edit) | < 10 KB / chat |
| Feature Flags | RAM (`FEATURE_CACHE`) | 1 read per 10 mins / chat | 600s (instant invalidation on edit) | < 1 KB / chat |
| Username Resolution | RAM (`USERNAME_CACHE_WRITE_GUARD`) | 1 write per hour / user | 3600s guard window | < 1 KB / user |
| Avatar Downloads | RAM (`AVATAR_CACHE`) | Telegram API download | 3600s (max 200 entries) | ~2-5 MB max total |
