from __future__ import annotations

import asyncio

import structlog
from telegram import Bot, ChatPermissions

from config import settings

logger = structlog.get_logger(__name__)


async def _unban_user(chat_id: int, user_id: int) -> None:
    bot = Bot(settings.bot_token)
    async with bot:
        await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)


async def _unmute_user(chat_id: int, user_id: int) -> None:
    bot = Bot(settings.bot_token)
    async with bot:
        await bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )


def unban_user(chat_id: int, user_id: int) -> dict[str, int | str]:
    """Unban user (immediate, no scheduling)."""
    try:
        asyncio.run(_unban_user(chat_id, user_id))
        logger.info("unban_completed", chat_id=chat_id, user_id=user_id)
        return {"status": "ok", "chat_id": chat_id, "user_id": user_id}
    except Exception as e:
        logger.error("unban_failed", chat_id=chat_id, user_id=user_id, error=str(e))
        return {"status": "error", "chat_id": chat_id, "user_id": user_id}


def unmute_user(chat_id: int, user_id: int) -> dict[str, int | str]:
    """Unmute user (immediate, no scheduling)."""
    try:
        asyncio.run(_unmute_user(chat_id, user_id))
        logger.info("unmute_completed", chat_id=chat_id, user_id=user_id)
        return {"status": "ok", "chat_id": chat_id, "user_id": user_id}
    except Exception as e:
        logger.error("unmute_failed", chat_id=chat_id, user_id=user_id, error=str(e))
        return {"status": "error", "chat_id": chat_id, "user_id": user_id}
