# Render Environment Configuration

| Variable | Description |
| :--- | :--- |
| `BOT_TOKEN` | Required. The Telegram Bot API token. |
| `BOT_MODE` | Optional. `webhook` or `polling`. Falls back based on `WEBHOOK_URL`. |
| `WEBHOOK_URL` / `RENDER_EXTERNAL_URL` | Required for webhook mode. The public URL of the Render service. |
| `WEBHOOK_SECRET` | Optional. Secret string to validate Telegram requests. |
| `WEBHOOK_PATH` | Optional. Route path for webhook. Default `/telegram/webhook`. |
| `WEBHOOK_PATH_TOKEN` | Optional. Additional path segment token for security. |
| `WEBHOOK_REQUIRE_SECRET_HEADER` | Optional. Boolean. Requires the secret header from Telegram. Default `True`. |
| `WEBHOOK_DROP_PENDING_UPDATES` | Optional. Boolean. Drop pending updates on restart. Default `True`. |
| `DATABASE_URL` | Required. Postgres connection string (e.g. `postgresql://user:pass@host/db`). |
| `REDIS_URL` | Required. Redis connection string (e.g. `redis://host:port/0`). |
| `CELERY_BROKER_URL` | Optional. Message broker URL for celery. |
| `CELERY_RESULT_BACKEND` | Optional. Result backend URL for celery. |
| `DATA_ENCRYPTION_KEY` | Required in `production`. Used for encryption. |
| `ENVIRONMENT` | Environment type (`local`, `test`, `production`). Default `local`. |
| `AUTO_MIGRATE_ON_STARTUP` | Boolean. Run Alembic migrations on startup. Default `False` in production. |
| `CAPTAIN_ID` | Owner Telegram ID. |
| `COMMANDER_IDS` | Comma-separated list of secondary admin Telegram IDs. |
| `SUDO_USERS` | Comma-separated list of global sudo users. |
| `ALLOWED_GROUP_IDS` | Infrastructure-level allowed group IDs (comma-separated). |
| `LOG_CHANNEL_ID` | Global log channel ID. |
| `MODERATION_PROVIDER` | `disabled` or `traditional_ml`. |
| `AI_MODERATION_ENABLED` | Boolean. Enable AI features. |
| `METRICS_API_KEY` | Required if you want to secure `/metrics`. |
