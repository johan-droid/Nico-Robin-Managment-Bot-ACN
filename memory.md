# Nico Robin Bot - Project Memory

## Project Overview
- **Name**: Nico Robin Bot
- **Version**: 0.2.0
- **Language**: Rust (2021 edition)
- **Framework**: teloxide 0.12
- **Database**: PostgreSQL with sqlx 0.7
- **Deployment**: Render / Railway (Docker)
- **Total Code**: ~4100 lines of Rust

## Current Status
**Last Updated**: 2026-07-22

### Architecture
- ✅ Rust backend with async/await (tokio)
- ✅ Connection pooling (PgPoolOptions) with startup migration runner
- ✅ Polling mode dispatcher (`dptree`)
- ✅ Role-based access control (Sudo > Captain > Commander > Normal)
- ✅ Multi-level sliding-window rate limiting (per-user-per-group + global)
- ✅ 29 functional commands across 9 active handler modules (fake placeholders removed)
- ✅ In-memory state caching (filter cache, swear cache, group cache, last welcome message cache)
- ✅ Comprehensive unit tests in `auth/rate_limiter.rs`, `auth/mod.rs`, and `entities/mod.rs`

### Dependencies
- tokio 1.38, serde 1.0, serde_json 1.0, envy 0.4, dotenvy 0.15
- sqlx 0.7 (runtime-tokio-rustls, postgres, chrono, json), teloxide 0.12 (macros, rustls, ctrlc_handler)
- chrono 0.4, tracing 0.1, tracing-subscriber 0.3 (json, env-filter)
- uuid 1.24.0 (v4)

### Database
- ✅ 10 migration files implemented (001-010)
- ✅ Tables: groups, notes, filters, warnings, welcome, profiles, swears, federations, features, flood
- ✅ Connection pool with retry logic (3 attempts, exponential backoff)
- ✅ SSL support with configurable mode (`sslmode=require`)
- ✅ Database verification on startup (`SELECT 1`)
- ✅ Flood settings: fully wired in DB layer & runtime `FloodTracker`

### Handlers Status
| Module | Commands | Status |
|--------|----------|--------|
| Core | /start, /help | ✅ Complete |
| Moderation | /ban, /unban, /kick, /mute, /unmute, /warn, /warns, /resetwarn, /slowmode, /del, /pin | ✅ Complete (All actions logged to channel) |
| Notes | /save, /get, /notes, /clear | ✅ Complete |
| Filters | /filter, /stop, /filters | ✅ Complete (Substring matching + in-memory cache) |
| Welcome | /setwelcome, /resetwelcome, /welcome, /setwelcomedm, /setfarewell, /farewell, /cleanwelcome, /welcometest | ✅ Complete (Event join/leave, DM support, clean_welcome auto-delete, {count}) |
| Profile | /profile, /setbio, /exportmydata, /deletemydata | ✅ Complete |
| Security | /setflood, /flood, /addswear, /delswear | ✅ Complete (Wired with flood tracker & swear cache) |
| Federation | /newfed, /joinfed | ✅ Complete |
| Features | /features, /enable, /disable, /toggle, /featureinfo, /myfeatures, /resetfeatures, /enablecategory, /disablecategory | ✅ Complete (Gates all command execution) |

### Permission Levels
- **Sudo**: Federation commands
- **Captain**: Filters, Welcome, Security, Features (toggle), moderation Telegram admin check
- **Commander**: Moderation actions, Notes (save/clear)
- **Normal**: /start, /help, /get, /notes, /profile, /setbio, /exportmydata, /deletemydata, /welcome, /farewell, /features (view)

### DB Modules
| Module | Functions |
|--------|-----------|
| groups | ensure_group |
| notes | save_note, get_note, list_notes, delete_note |
| filters | add_filter, remove_filter, list_filters |
| warnings | add_warning, get_warning_count, get_warnings, reset_warnings |
| welcome | set_welcome_message, get_welcome_settings, reset_welcome_message, set_welcome_dm_message, set_farewell_message, toggle_clean_welcome |
| profiles | get_or_create_profile, set_bio, delete_profile |
| swears | add_swear, remove_swear |
| federations | create_federation, join_federation, federation_exists |
| features | list_features, enable_feature, disable_feature, is_feature_enabled, reset_features |
| flood | get_flood_settings, set_flood_settings |

## Configuration
- Bot mode: polling (default)
- Bot name: "Nico Robin" (configurable via BOT_NAME)
- Default locale: en, Default prefix: /
- Database pool: 10 connections (default), connect timeout: 30s, recycle: 1800s
- Rate limits: 20/user, 300/global, cooldown: 30s, ban threshold: 5
- Auto-migrate on startup: enabled
- SSL required: true
- Warn threshold: 3 (auto-ban at 3 warnings)
- Environment variables: BOT_TOKEN, DATABASE_URL, SUDO_USERS, CAPTAIN_ID, COMMANDER_IDS, ALLOWED_GROUP_IDS, LOG_CHANNEL_ID

## File Structure
```
backend/
├── Cargo.toml
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── migrations/ (10 SQL files)
└── src/
    ├── main.rs (Entry point, preloading, polling dispatcher, cleanup tasks)
    ├── auth/ (mod.rs, rate_limiter.rs, flood_tracker.rs)
    ├── config/ (mod.rs - Settings struct, env deserialization, validation)
    ├── db/ (mod.rs + 10 modules: groups, notes, filters, warnings, welcome, profiles, swears, federations, features, flood)
    ├── entities/ (mod.rs - PgPool connection, retry logic, verify)
    ├── handlers/ (mod.rs + 9 modules: core, moderation, notes, filters, welcome, profile, security, federation, features)
    └── utils/ (mod.rs, logging.rs)
```

## Recent Backend Audit Updates (Phase A, B, C)
- Removed fake/placeholder broadcast handlers and broken command stubs
- Implemented multi-level sliding-window rate limiter in `auth/rate_limiter.rs`
- Implemented runtime flood tracker in `auth/flood_tracker.rs` with configurable mute/ban/warn actions
- Added async `resolve_username` helper in `auth/mod.rs` to resolve `@username` mentions from chat admins
- Implemented `clean_welcome` auto-deletion for previous welcome messages
- Added group caching in `AppState` to prevent redundant DB calls on every command
- Updated filter trigger matching to use substring/contains searching
- Added moderation action logging to `LOG_CHANNEL_ID` for all mod commands (ban, unban, kick, mute, unmute, warn, resetwarn, del, pin)
- Resolved `{count}` variable in welcome preview/test commands
