from __future__ import annotations

import asyncio
import logging
import os

from telegram.ext import Application

from core.cache import cache
from core.database import database
from core.event_bus import event_bus
from core.loader import ModuleLoader
from core.logging import setup_logging
from init_database import initialize_database

logger = logging.getLogger(__name__)
ALLOWED_UPDATES = ["message", "edited_message", "callback_query", "channel_post", "edited_channel_post"]


async def _refresh_admin_cache(application: Application) -> None:
    groups = await database.fetchall(
        """
        SELECT DISTINCT group_id FROM group_features
        UNION
        SELECT DISTINCT group_id FROM broadcast_targets
        """
    )
    for row in groups:
        group_id = row[0]
        try:
            admins = await application.bot.get_chat_administrators(group_id)
            cache.set(
                f"admin_cache:{group_id}",
                [member.user.id for member in admins],
                ttl=600,
            )
        except Exception:
            logger.exception("admin_cache_refresh_failed", extra={"group_id": group_id})


async def _refresh_admin_cache_job(context) -> None:
    await _refresh_admin_cache(context.job.data)


async def _bootstrap() -> Application:
    setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
    await initialize_database()
    application = Application.builder().token(os.environ["BOT_TOKEN"]).build()
    application.bot_data["db"] = database
    application.bot_data["cache"] = cache
    application.bot_data["event_bus"] = event_bus
    await event_bus.start()
    ModuleLoader(application).load_all()
    return application


async def main() -> None:
    application = await _bootstrap()
    await _refresh_admin_cache(application)
    application.job_queue.run_repeating(
        _refresh_admin_cache_job,
        interval=600,
        first=30,
        data=application,
        name="admin-cache-refresh",
    )
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=ALLOWED_UPDATES, drop_pending_updates=True)
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await database.close()
        await event_bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
