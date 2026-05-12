from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import select
from telegram import Bot, ChatPermissions

from config import settings
from database import async_session_factory
from models.group import Group
from tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _set_group_permissions(chat_id: int, can_send_messages: bool) -> None:
    bot = Bot(settings.bot_token)
    async with bot:
        permissions = ChatPermissions(can_send_messages=can_send_messages)
        await bot.set_chat_permissions(chat_id, permissions=permissions)

        message = (
            "The group is now sleeping..."
            if not can_send_messages
            else "The group is awake!"
        )
        await bot.send_message(chat_id, text=message)


async def _process_nightmode(enable: bool) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(Group).where(Group.nightmode_enabled))
        groups = result.scalars().all()

        for group in groups:
            try:
                await _set_group_permissions(
                    group.group_id, can_send_messages=not enable
                )
                logger.info(
                    "nightmode_processed", group_id=group.group_id, enabled=enable
                )
            except Exception as e:
                logger.error(
                    "nightmode_process_failed", group_id=group.group_id, error=str(e)
                )


def lock_group() -> dict[str, str]:
    """Enable night mode (lock group)."""
    try:
        asyncio.run(_process_nightmode(enable=True))
        return {"status": "ok"}
    except Exception as e:
        logger.error("nightmode_lock_failed", error=str(e))
        return {"status": "error", "error": str(e)}


def unlock_group() -> dict[str, str]:
    """Disable night mode (unlock group)."""
    try:
        asyncio.run(_process_nightmode(enable=False))
        return {"status": "ok"}
    except Exception as e:
        logger.error("nightmode_unlock_failed", error=str(e))
        return {"status": "error", "error": str(e)}


@celery_app.task
def lock_group_task():
    return lock_group()


@celery_app.task
def unlock_group_task():
    return unlock_group()
