from __future__ import annotations

import asyncio

import structlog
from telegram import Bot

from config import settings

logger = structlog.get_logger(__name__)


async def _send_announcement(chat_id: int, text: str) -> None:
    bot = Bot(settings.bot_token)
    async with bot:
        await bot.send_message(
            chat_id=chat_id, text=text, disable_web_page_preview=True
        )


def send_announcement(chat_id: int, text: str) -> dict[str, int | str]:
    """Send announcement (non-scheduled, requires manual invocation)."""
    try:
        asyncio.run(_send_announcement(chat_id, text))
        logger.info("announcement_sent", chat_id=chat_id)
        return {"status": "ok", "chat_id": chat_id}
    except Exception as e:
        logger.error("announcement_failed", chat_id=chat_id, error=str(e))
        return {"status": "error", "chat_id": chat_id, "error": str(e)}


def schedule_announcement(chat_id: int, text: str, eta) -> str:
    """Scheduling not available without Celery. Returns dummy task ID."""
    logger.warning(
        "schedule_announcement_not_supported",
        reason="celery_disabled",
        chat_id=chat_id,
    )
    return "disabled-no-celery"
