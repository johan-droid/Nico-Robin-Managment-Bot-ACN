# Agent Guide — Nico Robin Bot

## Architecture Overview

Nico Robin is a Telegram group management bot built with `python-telegram-bot` (PTB) v21+, SQLAlchemy async, PostgreSQL, and Redis.

### Directory Structure
```
src/bot/
├── main.py                  # Entry point, command menu (_BOT_COMMANDS), webhook/polling modes
├── config.py                # Pydantic settings (env vars, validation)
├── database.py              # SQLAlchemy async engine, session factory
├── models/                  # SQLAlchemy ORM models (group, user, warn, etc.)
├── bot/
│   ├── app.py               # Application factory — middleware chain registration
│   ├── dispatcher.py        # Plugin loader + handler registration
│   ├── handlers_list.py     # COMMAND_BINDINGS — fallback command registry
│   ├── middleware/
│   │   ├── request_logger.py    # group=-3: logs all updates
│   │   ├── group_guard.py       # group=-2: ALLOWED_GROUP_IDS check
│   │   ├── security.py          # rate_limit_check
│   │   ├── command_guard.py     # input sanitization
│   │   ├── feature_gate.py      # feature toggle enforcement
│   │   └── error_handler.py     # global exception handler
│   └── plugins/              # 26 plugin modules
│       ├── admin.py          # ban, unban, kick, mute, unmute, warn, warns, resetwarn, pin, del, slowmode
│       ├── filters.py        # Custom word filters
│       ├── welcome.py        # Welcome/farewell/rules
│       ├── notes.py          # Saved notes + hashtag handler
│       ├── flood_control.py  # Anti-flood
│       ├── swear_words.py    # Swear word detection
│       ├── ai_mod.py         # AI-powered moderation
│       ├── federation.py     # Multi-group federation
│       ├── scheduler.py      # Timed announcements
│       ├── stats.py          # Group statistics
│       ├── user_info.py      # /id, /whois, /info
│       ├── settings.py       # Group settings (locale, warnlimit, etc.)
│       ├── locks.py          # Media type locks
│       ├── captcha.py        # New member verification
│       ├── purge.py          # Bulk message deletion
│       ├── nightmode.py      # Night mode
│       ├── channel_guard.py  # Channel auto-purge
│       ├── command_menu.py   # /commands, /allcommands
│       ├── fun.py            # /ping, /robin
│       ├── nico_moments.py   # RP commands (pat, slap, hug, etc.)
│       ├── profile.py        # User profiles
│       ├── feature_management.py # Feature toggle system
│       ├── points.py         # Points/levels/apploids (ACN-only)
│       ├── flirting.py       # Flirting system (ACN-only)
│       ├── bot_friendship.py # Yamato friendship (ACN-only)
│       ├── acn_loyalty.py    # ACN loyalty/roles (ACN-only)
│       └── acn_broadcast.py  # Channel broadcast (ACN-only)
├── services/                 # Business logic layer
│   ├── acn_service.py        # ACN whitelist, decorators (admin_captain_commander_only, etc.)
│   ├── feature_service.py    # Feature toggle logic
│   └── ...                   # Other services
├── utils/                    # Helpers
│   └── decorators.py         # @admin_only, @group_only, @require_admin, etc.
└── i18n/                     # Translations (en.json, hi.json, ja.json)
```

## Key Conventions

### Handler Registration (Two-Tier)
1. **Plugin `register()`**: Each plugin that handles commands registers `CommandHandler`s in its own `register(app)` function
2. **`COMMAND_BINDINGS`** (`handlers_list.py`): Fallback registry for commands whose plugins don't self-register

### Middleware Pipeline (order matters)
```
group=-3  request_logger     (log all updates)
group=-2  group_guard        (block unauthorized groups)
group=-1  _rate_limit_gate   (rate_limit → command_guard → feature_gate)
group=0   plugin handlers    (all CommandHandlers)
group=1   track_message      (passive stats)
```
Error handlers: `group_guard_error_handler` → `global_error_handler`

### Decorator Stack Pattern
Commands use stacked decorators from bottom to top:
```python
@group_only            # Must be in a group chat
@admin_only           # Must be a Telegram group admin
@bot_rights_required  # Bot must have specific permission
async def command(...)
```

### Important: Two Separate Access Control Systems
1. **`ALLOWED_GROUP_IDS`** env var — checked by `group_guard.py` middleware (group-level gate)
2. **ACN whitelist** (DB table `acn_whitelist`) — checked by `@acn_only` decorator in `acn_service.py` (service-level gate)

Do NOT confuse these. `ALLOWED_GROUP_IDS` controls which groups can access the bot. ACN whitelist controls ACN-specific commands.

## Commands Overview

All documented commands are in `docs/FEATURES.md`. The Telegram menu (`_BOT_COMMANDS` in `main.py`) has exactly 100 entries due to Telegram's limit.

### Moderation Commands (admin-only)
`ban`, `unban`, `kick`, `mute`, `unmute`, `warn`, `warns`, `resetwarn`, `slowmode`, `del`, `pin`, `purge`, `filter`, `stop`, `filters`, `filteraction`, `toggleai`, `setflood`, `setfloodmode`, `flood`, `captcha`, `setwarnlimit`, `setwarnaction`

### Content Commands
`setwelcome`, `resetwelcome`, `welcome`, `setfarewell`, `farewell`, `cleanwelcome`, `welcometest`, `setrules`, `rules`, `save`, `get`, `notes`, `clear`

### Info Commands
`stats`, `id`, `whois`, `info`, `ping`, `robin`

### ACN-Only Commands (require ACN whitelist)
`points`, `leaderboard`, `award`, `apploids`, `flirt`, `flirt_stats`, `bond_with_yamato`, `yamato_status`, `acn_status`, `loyalty_leaderboard`, etc.

## Deployment

- **Platform**: Render (webhook mode)
- **URL**: `https://nico-robin-managment-bot.onrender.com`
- **DB**: PostgreSQL (Render managed)
- **Redis**: Optional, falls back to no-op for rate limiting
- **Config**: All via env vars (see `docs/03_render_env.md`)

### Render Env Vars Required
```
BOT_TOKEN=...
ALLOWED_GROUP_IDS=-1004380308308
CAPTAIN_ID=7575403902
COMMANDER_IDS=6449644059
SUDO_USERS=7575403902,6449644059
DATABASE_URL=postgresql+asyncpg://...
```

### Build Cache
First deploy needs `dockerBuildFlags: --no-cache` in `render.yaml`. Can be removed after successful build.

## Known Issues / Gotchas

1. **Telegram 100-command menu limit**: Bot commands in `_BOT_COMMANDS` must stay ≤ 100
2. **`log_channel_id=0`**: Treated as disabled (don't send to channel ID 0)
3. **`_feature_blocked`**: Raised by feature gate as `RuntimeError`, classified as IGNORE in error handler
4. **Group defaults**: All auto-response features (welcome, farewell, flood, swear words) default to OFF
5. **`@acn_only`** on ACN commands: Separately checked from `ALLOWED_GROUP_IDS`
