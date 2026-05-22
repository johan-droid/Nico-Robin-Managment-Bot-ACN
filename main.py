from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from core.admin_cache import AdminCache
from core.broadcast_handler import handle_channel_post
from core.cache import Cache
from core.database import DatabaseManager
from core.event_bus import EventBus
from core.loader import ModuleLoader

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def _refresh_admin_cache_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_cache: AdminCache = context.application.bot_data["admin_cache"]
    await admin_cache.refresh_known_groups(context.bot)


async def _on_startup(application: Application) -> None:
    db: DatabaseManager = await DatabaseManager.get_instance()
    await db.initialize()
    cache = Cache()
    event_bus = EventBus()
    await event_bus.start(worker_count=2)
    admin_cache = AdminCache(ttl_seconds=300)

    application.bot_data["db"] = db
    application.bot_data["cache"] = cache
    application.bot_data["event_bus"] = event_bus
    application.bot_data["admin_cache"] = admin_cache

    loader = ModuleLoader(modules_dir="modules")
    loader.load_and_register(application)
    application.bot_data["module_loader"] = loader

    application.add_handler(
        MessageHandler(filters.UpdateType.CHANNEL_POST, handle_channel_post),
        group=100,
    )

    if application.job_queue is not None:
        application.job_queue.run_repeating(
            _refresh_admin_cache_job,
            interval=300,
            first=60,
            name="admin-cache-refresh",
        )

    logger.info(
        "startup_complete", extra={"modules": list(loader.loaded_modules.keys())}
    )


async def _on_shutdown(application: Application) -> None:
    event_bus: EventBus | None = application.bot_data.get("event_bus")
    db: DatabaseManager | None = application.bot_data.get("db")
    if event_bus is not None:
        await event_bus.stop()
    if db is not None:
        await db.close()
    logger.info("shutdown_complete")


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("update_error", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "An internal error occurred while processing that command."
        )


def build_application() -> Application:
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    app = (
        Application.builder()
        .token(token)
        .post_init(_on_startup)
        .post_shutdown(_on_shutdown)
        .build()
    )
    app.add_error_handler(_error_handler)
    return app


def main() -> None:
    app = build_application()
    app.run_polling(
        allowed_updates=[
            "message",
            "edited_message",
            "channel_post",
            "edited_channel_post",
            "callback_query",
            "chat_member",
        ]
    )


if __name__ == "__main__":
    main()
