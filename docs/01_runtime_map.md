# Runtime Map

## Entrypoint
The bot is started using `main.py` at the root, which just delegates to `src.bot.main:main()`.

## Runtime Modes
Controlled by `BOT_MODE` or inference from `WEBHOOK_URL` in `src.bot.config.py`.
*   **Webhook Mode:** Uses FastAPI and `uvicorn` to run a combined application (Telegram via FastAPI + Socket.IO). The URL registered is built using `webhook_base_url` + `webhook_path` + optional `webhook_path_token`.
*   **Polling Mode:** Uses Telegram's built-in PTB polling loop. Automatically deregisters existing webhooks.

## Webhook Flow
*   Incoming webhook HTTP requests go to FastAPI in `src/bot/gateway/webhook.py`.
*   Middlewares (like `SecurityHeadersMiddleware`, `RequestSizeLimitMiddleware`) execute.
*   Token/secret validation (`x-telegram-bot-api-secret-token` header and path tokens).
*   Delegation to `ptb_app.process_update(update)`.

## FastAPI Routes
*   `/`, `/health`, `/metrics`, `/websocket/stats`, `/diagnostics` (Safe healthcheck)
*   `/telegram/webhook`, `/telegram/webhook/{path_token}`, `/webhook` (Telegram Webhook endpoints)

## Middleware Order (PTB)
Defined in `src/bot/bot/app.py`:
1.  **-3**: `log_update_details` (Logs all updates).
2.  **-2**: `group_guard` (Blocks unauthorized groups based on `ALLOWED_GROUP_IDS`).
3.  **-1**: `_rate_limit_gate` (Rate limiting check, then delegates to `command_input_guard` and `feature_gate_check`).
4.  **0**: All plugin command handlers (`register_all_handlers`).
5.  **1**: `track_message` (Passive message tracker).

## Command Registry
Maintained centrally in `src/bot/bot/handlers_list.py` (`COMMAND_BINDINGS`). Note: Telegram command menu is limited to 100 via `_BOT_COMMAND_MENU_LIMIT` in `src.bot.main.py`.

## Infrastructure Roles
*   **Database:** Asyncpg/SQLAlchemy (PostgreSQL).
*   **Redis:** Caching (`ACNService` roles, rate limiter limits).
*   **Celery:** Background tasks (`celery_app.py`, `announce_tasks.py`).
*   **WebSocket:** Real-time updates via Socket.IO.
