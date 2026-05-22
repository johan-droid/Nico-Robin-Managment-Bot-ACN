from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .cache import cache
from .database import database

logger = logging.getLogger(__name__)


async def _retry(action, attempts: int = 3, delay: float = 0.5):
    last_exc: Exception | None = None
    for index in range(attempts):
        try:
            return await action()
        except TelegramError as exc:
            last_exc = exc
            if index + 1 < attempts:
                await asyncio.sleep(delay * (index + 1))
        except Exception as exc:
            last_exc = exc
            break
    if last_exc is not None:
        raise last_exc


async def _active_targets() -> list[int]:
    rows = await database.fetchall("SELECT group_id FROM broadcast_targets WHERE is_active = 1")
    return [row[0] for row in rows]


async def _is_source_channel(channel_id: int) -> bool:
    row = await database.fetchone(
        "SELECT 1 FROM broadcast_sources WHERE channel_id = ? AND is_active = 1",
        (channel_id,),
    )
    return row is not None


async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.channel_post
    if message is None or message.chat is None:
        return False

    channel_id = message.chat.id
    message_id = message.message_id
    if not await _is_source_channel(channel_id):
        return False

    cache_key = f"broadcast:last:{channel_id}"
    last_message_id = cache.get(cache_key)
    if last_message_id == message_id:
        logger.info("broadcast_deduplicated", extra={"channel_id": channel_id, "message_id": message_id})
        return True

    targets = await _active_targets()
    if not targets:
        return False

    delivered_any = False
    for group_id in targets:
        if group_id == channel_id:
            continue

        async def copy_action() -> Any:
            return await context.bot.copy_message(
                chat_id=group_id,
                from_chat_id=channel_id,
                message_id=message_id,
            )

        try:
            copied = await _retry(copy_action)
            copied_id = getattr(copied, "message_id", None)
            if copied_id is None and isinstance(copied, dict):
                copied_id = copied.get("message_id")
            await database.execute(
                """
                INSERT OR REPLACE INTO broadcast_deliveries
                (source_channel_id, source_message_id, destination_group_id, destination_message_id, destination_message_kind)
                VALUES (?, ?, ?, ?, ?)
                """,
                (channel_id, message_id, group_id, int(copied_id or 0), "copy"),
            )
            delivered_any = True
        except Exception:
            logger.exception(
                "broadcast_delivery_failed",
                extra={"channel_id": channel_id, "message_id": message_id, "group_id": group_id},
            )

    cache.set(cache_key, message_id, ttl=3600)
    await database.execute(
        """
        INSERT OR REPLACE INTO broadcast_state (channel_id, last_message_id, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        """,
        (channel_id, message_id),
    )
    return delivered_any


async def handle_edited_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.edited_channel_post
    if message is None or message.chat is None:
        return False

    channel_id = message.chat.id
    message_id = message.message_id
    rows = await database.fetchall(
        """
        SELECT destination_group_id, destination_message_id, destination_message_kind
        FROM broadcast_deliveries
        WHERE source_channel_id = ? AND source_message_id = ?
        """,
        (channel_id, message_id),
    )
    if not rows:
        return False

    edited_text = message.text or message.caption or ""
    successful = 0
    for group_id, destination_message_id, kind in rows:
        try:
            if kind == "copy" and message.text:
                await _retry(
                    lambda: context.bot.edit_message_text(
                        chat_id=group_id,
                        message_id=destination_message_id,
                        text=edited_text,
                    )
                )
            elif message.caption is not None:
                await _retry(
                    lambda: context.bot.edit_message_caption(
                        chat_id=group_id,
                        message_id=destination_message_id,
                        caption=edited_text,
                    )
                )
            successful += 1
        except Exception:
            logger.exception(
                "broadcast_edit_failed",
                extra={"channel_id": channel_id, "message_id": message_id, "group_id": group_id},
            )
    return successful > 0
