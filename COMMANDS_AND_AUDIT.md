# 🤖 Nico Robin Bot — Command Reference & Audit Report

> **Project:** Nico Robin Management Bot (ACN)  
> **Stack:** Rust · Axum · Tokio · PostgreSQL (Neon) · Telegram Bot API  
> **Last Updated:** 2026-07-31

---

## 📑 Table of Contents

1. [Permission Levels](#-permission-levels)
2. [Core Commands](#-core-commands)
3. [Profile Commands](#-profile-commands)
4. [Notes Commands](#-notes-commands)
5. [Filter Commands](#-filter-commands)
6. [Welcome & Farewell Commands](#-welcome--farewell-commands)
7. [Security Commands](#-security-commands)
8. [Moderation Commands](#-moderation-commands)
9. [Feature Toggle Commands](#-feature-toggle-commands)
10. [Federation Commands](#-federation-commands)
11. [Full Audit Report](#-full-audit-report)
12. [How to Run](#-how-to-run)

---

## 🔑 Permission Levels

| Level | Who | Description |
|-------|-----|-------------|
| 🌍 **Everyone** | Any chat member | No restrictions — open to all |
| 🛡️ **Admin** | Group admins & bot sudo users | Requires Telegram admin rights in the group |
| 👑 **Sudo** | IDs listed in `SUDO_USERS` env var | Bot-level super admins; bypass all checks |

> **Target Resolution:** Most admin commands accept a reply to a message **or** `@username` as the target. The bot will attempt to resolve the username to a user ID automatically.

---

## 🏠 Core Commands

> **File:** `backend/src/handlers/core.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/start` | `/start` | 🌍 Everyone | Sends a welcome greeting with bot introduction |
| `/help` | `/help` | 🌍 Everyone | Displays a categorised, formatted list of all available commands |

**Implementation Notes:**
- `/help` generates its output dynamically from a static `sections` array — no DB query needed.
- Both commands use `ParseMode::MarkdownV2` with `escape_md_v2()` for safe formatting.

**Work Progress:** ✅ Complete

---

## 👤 Profile Commands

> **File:** `backend/src/handlers/profile.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/profile` | `/profile` or `/profile @user` | 🌍 Everyone | Shows a rich profile card with the user's profile picture, username, group role, ID and bio for yourself or a target user |
| `/setbio` | `/setbio <text>` | 🌍 Everyone | Sets your own bio (stored in DB under your user ID) |
| `/exportmydata` | `/exportmydata` | 🌍 Everyone | Exports your stored profile data as a pretty-printed JSON block |
| `/deletemydata` | `/deletemydata` | 🌍 Everyone | Permanently deletes all your stored profile data from the DB |

**Implementation Notes:**
- `/profile` falls back to the sender if no target is specified, and resolves replies / `@username` targets via admins + the username cache.
- The profile card includes the user's **profile picture** (sent as a photo with the card as caption), **username**, **group role** (Owner / Admin / Member / Banned / Restricted), user ID and stored bio.
- `/exportmydata` calls `get_or_create_profile()`, so it always returns data (creates one if missing).
- `/deletemydata` returns a clear "No data found" if the profile doesn't exist.

**Work Progress:** ✅ Complete

---

## 📝 Notes Commands

> **File:** `backend/src/handlers/notes.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/save` | `/save <name> <content>` | 🛡️ Admin | Saves a named note scoped to the chat |
| `/get` | `/get <name>` | 🌍 Everyone | Retrieves a saved note by name and posts its content |
| `/notes` | `/notes` | 🌍 Everyone | Lists all note names saved in the current chat |
| `/clear` | `/clear <name>` | 🛡️ Admin | Deletes a note by name; responds with "not found" if absent |

**Implementation Notes:**
- Notes are scoped per `chat_id` — isolated between groups.
- `/save` uses `splitn(3, ' ')` so content can contain spaces.
- `/get` returns the raw stored content without escaping — supports rich text.

**Work Progress:** ✅ Complete

---

## 🔍 Filter Commands

> **File:** `backend/src/handlers/filters.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/filter` | `/filter <trigger> <response>` | 🛡️ Admin | Adds an auto-reply rule: when `trigger` appears in a message, bot replies with `response` |
| `/stop` | `/stop <trigger>` | 🛡️ Admin | Removes an active filter by its trigger text |
| `/filters` | `/filters` | 🌍 Everyone | Lists all active filters for the current chat with their trigger → response pairs |

**Implementation Notes:**
- Triggers are matched against incoming message text in `handlers/mod.rs`.
- Uses `splitn(3, ' ')` so responses can contain spaces.
- Stored and queried via `crate::db::filters`.

**Work Progress:** ✅ Complete

---

## 👋 Welcome & Farewell Commands

> **File:** `backend/src/handlers/welcome.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/setwelcome` | `/setwelcome <message>` | 🛡️ Admin | Sets the welcome message sent when a new member joins. Supports `{user}`, `{group}`, `{count}` variables |
| `/resetwelcome` | `/resetwelcome` | 🛡️ Admin | Clears the welcome message (bot goes silent on new joins) |
| `/welcome` | `/welcome` | 🛡️ Admin | Previews the current welcome message as-is |
| `/setwelcomedm` | `/setwelcomedm <message>` | 🛡️ Admin | Sets a DM message sent privately to each new member. Supports `{user}`, `{group}` |
| `/setfarewell` | `/setfarewell <message>` | 🛡️ Admin | Sets the farewell message when a member leaves. Supports `{user}`, `{group}` |
| `/farewell` | `/farewell` | 🛡️ Admin | Previews the current farewell message |
| `/cleanwelcome` | `/cleanwelcome` | 🛡️ Admin | Toggles auto-deletion of welcome messages after **60 seconds** |
| `/welcometest` | `/welcometest` | 🛡️ Admin | Fires a test welcome with your own name, group name, and real member count |

**Template Variables:**

| Variable | Replaced With |
|----------|--------------|
| `{user}` | New member's first name |
| `{group}` | Chat title |
| `{count}` | Current member count (fetched live) |

**Auto-Events (no command needed):**
- `handle_new_member` — triggered automatically when `new_chat_members` appears in an update.
- `handle_left_member` — triggered automatically when `left_chat_member` appears.

**Work Progress:** ✅ Complete

---

## 🔒 Security Commands

> **File:** `backend/src/handlers/security.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/setflood` | `/setflood <count>` | 🛡️ Admin | Sets max messages per user in a 10-second window. Use `0` to disable flood protection |
| `/flood` | `/flood` | 🛡️ Admin | Displays current flood settings: limit, window (seconds), and action mode |
| `/addswear` | `/addswear <word>` | 🛡️ Admin | Adds a word to the per-chat swear filter (case-insensitive, stored lowercase) |
| `/delswear` | `/delswear <word>` | 🛡️ Admin | Removes a word from the swear filter |
| `/report` | `/report` (reply to message) | 🌍 Everyone | Flags a message to the group's admins |

**Flood Protection Modes:**

| Mode | Behaviour |
|------|-----------|
| `warn` | Warns the user (default when limit > 0) |
| `off` | Disables flood checking |

**Implementation Notes:**
- Flood and swear word lists are loaded into **in-memory cache** at startup and invalidated on write commands — avoiding per-message DB queries.
- Cache lives in `NativeState` (Axum) / `ChatState` (Wasm).

**Work Progress:** ✅ Complete

---

## 🔨 Moderation Commands

> **File:** `backend/src/handlers/moderation.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/ban` | `/ban @user` or reply | 🛡️ Admin | Permanently bans a user from the chat |
| `/unban` | `/unban @user` or reply | 🛡️ Admin | Lifts a ban — user can rejoin via invite |
| `/kick` | `/kick @user` or reply | 🛡️ Admin | Removes a user from the chat without a permanent ban (can rejoin) |
| `/mute` | `/mute @user` or reply | 🛡️ Admin | Restricts all chat permissions (`ChatPermissions::empty()`) |
| `/unmute` | `/unmute @user` or reply | 🛡️ Admin | Restores all chat permissions (`ChatPermissions::all()`) |
| `/warn` | `/warn @user [reason]` or reply | 🛡️ Admin | Issues a warning. Auto-bans when warn threshold is reached and resets the counter |
| `/warns` | `/warns @user` or reply | 🛡️ Admin | Shows warning count and list of reasons for a user |
| `/resetwarn` | `/resetwarn @user` or reply | 🛡️ Admin | Clears all warnings for a user |
| `/slowmode` | `/slowmode <seconds>` | 🛡️ Admin | Sets chat slow mode delay. Use `0` to disable |
| `/purge` | `/purge <count>` or reply | 🛡️ Admin | Deletes the replied-to message and everything after it, or the last N messages |
| `/tmute` | `/tmute @user <duration>` | 🛡️ Admin | Temporarily mutes a user for a set time (e.g. 30m, 2h, 1d) |
| `/tban` | `/tban @user <duration>` | 🛡️ Admin | Temporarily bans a user for a set time (e.g. 1h, 1d, 1w) |
| `/del` | `/del` (reply to message) | 🛡️ Admin | Deletes the replied-to message and the `/del` command itself |
| `/pin` | `/pin` (reply to message) | 🛡️ Admin | Pins the replied-to message and deletes the `/pin` command |
| `/unpin` | `/unpin` or `/unpin all` | 🛡️ Admin | Unpins a specific message or clears all pinned messages |
| `/autowarnon` | `/autowarnon` | 🛡️ Admin | Enables automatic warnings for repeat offenders |
| `/autowarnoff` | `/autowarnoff` | 🛡️ Admin | Disables automatic warnings |
| `/kickme` | `/kickme` | 🌍 Everyone | Removes yourself from the group |

**Warn Auto-Ban Logic:**
```
warn_count >= warn_threshold  →  auto-ban + reset warns
```
- `warn_threshold` is configured in `Settings` (loaded from env/config).
- All actions are logged to `LOG_CHANNEL_ID` via `log_mod_action()`.

**Work Progress:** ✅ Complete

---

## ⚙️ Feature Toggle Commands

> **File:** `backend/src/handlers/features.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/features` | `/features` | 🌍 Everyone | Lists all feature overrides in the current chat (ON/OFF) |
| `/enable` | `/enable <feature>` | 🛡️ Admin | Enables a named feature for this chat |
| `/disable` | `/disable <feature>` | 🛡️ Admin | Disables a named feature |
| `/enablecategory` | `/enablecategory <category>` | 🛡️ Admin | Enables every feature in a category at once |
| `/disablecategory` | `/disablecategory <category>` | 🛡️ Admin | Disables every feature in a category at once |
| `/toggle` | `/toggle <feature>` | 🛡️ Admin | Reads current state and flips it |
| `/featureinfo` | `/featureinfo` | 🌍 Everyone | Shows all feature categories and the features they contain |
| `/myfeatures` | `/myfeatures` | 🌍 Everyone | Shows enabled/disabled/total counts for this chat |
| `/resetfeatures` | `/resetfeatures` | 🛡️ Admin | Removes all feature overrides — restores all to default (enabled) |

**Feature Categories:**

| Category | Features |
|----------|---------|
| `moderation` | ban, unban, kick, mute, unmute, warn, slowmode, purge, tmute, tban, kickme, pin, unpin, del, staff |
| `notes` | save, get, notes, clear |
| `filters` | filter, stop, filters |
| `welcome` | welcome, farewell |
| `security` | flood, swear, report |
| `rules` | setrules, rules, clearrules |
| `locks` | lock, unlock, locks |
| `profile` | profile, setbio |
| `federation` | newfed, joinfed, gban, ungban, gbans |

**Work Progress:** ✅ Complete

---

## 🌐 Federation Commands

> **File:** `backend/src/handlers/federation.rs`

| Command | Syntax | Permission | Description |
|---------|--------|------------|-------------|
| `/newfed` | `/newfed <name>` | 🛡️ Admin | Creates a new federation with the given name; returns a unique 8-character federation ID |
| `/joinfed` | `/joinfed <fed_id>` | 🛡️ Admin | Links the current group to an existing federation by its ID |
| `/gban` | `/gban @user <reason>` | 🛡️ Admin | Bans a user from every group the bot manages |
| `/ungban` | `/ungban @user` | 🛡️ Admin | Removes a user from the global ban list |
| `/gbans` | `/gbans` | 🛡️ Admin | Lists all globally banned users |

**Implementation Notes:**
- Federation IDs are the first 8 characters of a UUID v4.
- `join_federation` returns `false` (already a member) or `true` (newly joined).
- Federation data is stored in `crate::db::federations`.

**Work Progress:** ✅ Complete — *federation ban propagation across groups is not yet implemented*

---

## 📊 Full Audit Report

### Architecture Overview

```
Telegram Webhook
       │
       ▼
  Axum Router (main.rs)
       │
       ▼
  handle_message (handlers/mod.rs)
       │
  ┌────┴────┐
  ▼         ▼
Flood     Command
Check      Rate Limit
  │         │
  └────┬────┘
       ▼
  Feature Check
       │
       ▼
  Command Handler
  (core / profile / notes / filters /
   welcome / security / moderation /
   features / federation)
       │
       ▼
  DB (PostgreSQL via Neon)
```

### Module Status

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Telegram API client | `telegram/api.rs` | ✅ Complete | Custom lightweight client; no aiogram/teloxide |
| Update parsing | `telegram/update.rs` | ✅ Complete | Manual deserialization |
| Auth & permission check | `auth/mod.rs` | ✅ Complete | Admin check via `getChatMember` API |
| Rate limiter | `auth/rate_limiter.rs` | ✅ Complete | Constants hard-coded; no env dependency |
| State management | `main.rs` / `lib.rs` | ✅ Complete | `NativeState` (Axum) + `ChatState` (Wasm DO) |
| In-memory cache | `main.rs` | ✅ Complete | Flood settings + swear words cached per chat |
| Handler dispatch | `handlers/mod.rs` | ✅ Complete | Single `handle_message` gate with flood → rate limit → feature → command pipeline |
| Core commands | `handlers/core.rs` | ✅ Complete | `/start`, `/help` |
| Profile commands | `handlers/profile.rs` | ✅ Complete | `/profile`, `/setbio`, `/exportmydata`, `/deletemydata` |
| Notes | `handlers/notes.rs` | ✅ Complete | `/save`, `/get`, `/notes`, `/clear` |
| Filters | `handlers/filters.rs` | ✅ Complete | `/filter`, `/stop`, `/filters` |
| Welcome/Farewell | `handlers/welcome.rs` | ✅ Complete | All 8 commands + auto-events |
| Security | `handlers/security.rs` | ✅ Complete | `/setflood`, `/flood`, `/addswear`, `/delswear` |
| Moderation | `handlers/moderation.rs` | ✅ Complete | 18 admin commands + `/kickme` with logging |
| Feature toggles | `handlers/features.rs` | ✅ Complete | All 9 commands |
| Federation | `handlers/federation.rs` | 🟡 Partial | Create/join done; cross-fed ban propagation missing |
| DB — profiles | `db/profiles.rs` | ✅ Complete | CRUD for user profiles |
| DB — notes | `db/notes.rs` | ✅ Complete | Chat-scoped note storage |
| DB — filters | `db/filters.rs` | ✅ Complete | Chat-scoped filter storage |
| DB — warnings | `db/warnings.rs` | ✅ Complete | Warning add/get/reset |
| DB — flood | `db/flood.rs` | ✅ Complete | Flood settings per chat |
| DB — swears | `db/swears.rs` | ✅ Complete | Swear word list per chat |
| DB — welcome | `db/welcome.rs` | ✅ Complete | Welcome/farewell settings |
| DB — features | `db/features.rs` | ✅ Complete | Feature override storage |
| DB — federations | `db/federations.rs` | 🟡 Partial | Create/join; no ban sync |
| Utils | `utils/mod.rs` | ✅ Complete | `escape_md_v2`, `spawn_task` portable helper |
| Config | `config/mod.rs` | ✅ Complete | Loaded from env at startup |
| Env configuration | `.env.local` | ✅ Complete | Trimmed to only essential variables |
| Rate limits | `auth/rate_limiter.rs` | ✅ Complete | Hard-coded constants |

### Completed Improvements (This Session)

- [x] Moved all rate limit values from env to compile-time constants
- [x] Removed rate limit env vars from `.env.local`
- [x] Implemented `NativeState` with `Mutex<HashMap>` for in-memory state
- [x] Implemented `spawn_task` portable async helper (fixes Wasm panic)
- [x] Swear words and flood settings cached in-memory (cache invalidated on write)
- [x] Cleaned up unnecessary deployment config files
- [x] Added `dotenvy` auto-load in `main.rs`

### Outstanding Items

- [ ] **Federation ban propagation** — bans in one group should apply to all groups in the same federation
- [ ] **Unit tests** — no automated tests exist yet; add tests for auth, rate limiter, and DB modules
- [ ] **Integration test** — verify each command end-to-end against a test bot
- [ ] **Moderation log formatting** — `log_mod_action` sends plain text; upgrade to MarkdownV2 embeds
- [ ] **`/warns` threshold source** — currently reads `WARN_THRESHOLD` env var directly inside handler; should use the `Settings` struct for consistency
- [ ] **Binary file cleanup** — manually run: `rm "Nico Robi  Documentation v3.pdf"` from project root

---

## 🚀 How to Run

```bash
# Navigate to the backend directory
cd "backend"

# Ensure .env.local is populated (see .env.local in the backend folder)
# Build and run the bot binary
cargo run --release --bin nico_robin_bot

# To run the DB migrations separately:
# cargo run --release --bin migrate
```

> The bot starts an Axum HTTP server on `PORT` (default `8000`) and listens for Telegram webhook POSTs.  
> Make sure your `BOT_TOKEN` and `DATABASE_URL` are set in `.env.local`.

### Required `.env.local` Variables

| Variable | Purpose |
|----------|---------|
| `BOT_TOKEN` | Telegram bot API token |
| `DATABASE_URL` | PostgreSQL connection string (Neon) |
| `SUDO_USERS` | Comma-separated list of super-admin Telegram user IDs |
| `ALLOWED_GROUP_IDS` | Comma-separated allowed chat IDs (or leave blank for all) |
| `LOG_CHANNEL_ID` | Channel ID for moderation logs (`0` = disabled) |
| `BOT_NAME` | Display name used in messages |
| `ENVIRONMENT` | `local` or `production` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARN`, `ERROR` |

---

*Documentation generated by Antigravity — AI coding assistant.*
