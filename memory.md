# Nico Robin Bot - Project Memory Vault

## Project Overview
- **Name**: Nico Robin Management Bot (ACN)
- **Version**: 0.2.0
- **Language**: Rust (2021 edition)
- **Framework**: Tokio 1.38 (async runtime) + Axum 0.7 + reqwest
- **Database**: PostgreSQL (Neon Serverless Postgres) via `tokio-postgres` 0.7 & `deadpool-postgres` 0.14
- **Deployment Platform**: Heroku Basic Dyno (512 MB RAM limit, 1 vCPU) / Docker
- **Operating Modes**: Webhook & Telegram Long-Polling (`BOT_MODE=polling` / `webhook`)

---

## Current Status & Progress Milestones
**Last Updated**: 2026-09-02

### Architecture Updates
- ✅ **Tokio Async Architecture**: Fully running on multi-threaded Tokio runtime with native TLS (`tokio-postgres-rustls`).
- ✅ **Database Migration Engine**: Automated SQL migrations via `backend/src/bin/migrate.rs` (26 active migration scripts).
- ✅ **Neon Free Tier Optimization**: Zero-waste database access pattern implemented.
  - `PERSIST_MESSAGE_HISTORY=false`: RAM ring buffers handle `/q` quoting without issuing SQL `INSERT`s on every message.
  - `ENABLE_COMMAND_LOGGING=false`: Opt-in command execution audit logging.
  - Extended Cache TTLs: Filter, Swear, and Feature caches set to **10 minutes (600s)** with instant in-memory invalidation hooks on admin edits.
  - Username write guard set to **1 hour (3600s)** per user.
  - `DB_POOL_SIZE=5`: Reduced pool size allows Neon to auto-suspend after 5 mins of idle time.
- ✅ **Heroku Basic Dyno Memory Bounding**:
  - `HISTORY_MAX_PER_CHAT`: Bounded to 150 text messages per chat.
  - `AVATAR_CACHE`: Bounded to 200 entries max with TTL eviction.
  - Binary optimization (`opt-level = "z"`, `lto = true`, `strip = true`).

---

## Database & Caching Architecture

### Core Tables (26 Migrations Applied)
- `groups`, `notes`, `filters`, `warnings`, `welcome`, `profiles`, `swears`, `federations`, `feature_flags`, `flood_settings`
- `auto_warn_settings`, `message_history`, `rules`, `locks`, `gbans`, `username_cache`, `automation`, `economy`, `bounties`

### In-Memory Cache TTL & Strategy
| Cache Name | Scope | TTL / Write Guard | Invalidation Trigger |
|---|---|---|---|
| `FILTER_CACHE` | Per Chat | 600s (10 mins) | `/filter`, `/unfilter` |
| `SWEAR_CACHE` | Per Chat | 600s (10 mins) | `/addswear`, `/delswear` |
| `FEATURE_CACHE` | Per Chat | 600s (10 mins) | `/enable`, `/disable` |
| `USERNAME_CACHE_WRITE_GUARD` | Per User | 3600s (1 hr) | Natural expiry |
| `MESSAGE_HISTORY` | Per Chat | 150 msgs (RAM buffer) | Ring buffer eviction |
| `AVATAR_CACHE` | Per User | 3600s (max 200 items) | TTL / eviction |

---

## Environment & Configuration Variables
- `BOT_TOKEN`: Telegram Bot API Token.
- `DATABASE_URL`: Connection string (`postgresql://robin:password@localhost:5432/robin_db`).
- `BOT_MODE`: `polling` or `webhook`.
- `DB_POOL_SIZE`: Default `5` (optimized for Neon).
- `PERSIST_MESSAGE_HISTORY`: Default `false` (in-memory quoting).
- `ENABLE_COMMAND_LOGGING`: Default `false` (disables per-command DB inserts).
- `PORT`: HTTP server port (default `8000`).

---

## Progress Log / Batch History
- **Batch #1**: Repositories cleaned and project files structured into `backend/`.
- **Batch #2**: Verified database connection & initialized Postgres Docker + migrations 001-026.
- **Batch #3**: Telegram Bot Token authenticated (`@nicorobinACN_bot`).
- **Batch #4**: Implemented Neon Free Tier (100 compute hrs limit) and Heroku Basic Dyno (512MB RAM cap) optimizations.
- **Batch #5**: Documented Neon Free Tier Architecture ([FREE_TIER_NEON_STRUCTURE.md](file:///home/ashutoshsahoo/Downloads/Nico%20Robin%20Managment%20Bot/Nico-Robin-Managment-Bot-ACN/FREE_TIER_NEON_STRUCTURE.md)) and created workspace memory vault skill.
- **Batch #6**: Cleaned up and updated root [.gitignore](file:///home/ashutoshsahoo/Downloads/Nico%20Robin%20Managment%20Bot/Nico-Robin-Managment-Bot-ACN/.gitignore) and [backend/.gitignore](file:///home/ashutoshsahoo/Downloads/Nico%20Robin%20Managment%20Bot/Nico-Robin-Managment-Bot-ACN/backend/.gitignore) to remove invalid syntax artifacts and ensure all secrets/build targets are ignored.
