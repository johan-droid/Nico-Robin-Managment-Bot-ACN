from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.database import DatabaseManager

logger = logging.getLogger(__name__)


async def handle_channel_post(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Forward whitelisted channel posts to active target groups."""
    if update.channel_post is None:
        return

    db: DatabaseManager = context.application.bot_data["db"]
    post = update.channel_post
    source_channel_id = post.chat_id

    source = await db.fetchone(
        """
        SELECT channel_id
        FROM broadcast_sources
        WHERE channel_id = ? AND is_active = 1
        """,
        (source_channel_id,),
    )
    if source is None:
        return

    targets = await db.fetchall("""
        SELECT group_id
        FROM broadcast_targets
        WHERE is_active = 1
        """)
    if not targets:
        return

    for row in targets:
        group_id = int(row["group_id"])
        # Loop prevention guard: never relay back to source channel itself.
        if group_id == source_channel_id:
            continue
        try:
            await context.bot.copy_message(
                chat_id=group_id,
                from_chat_id=source_channel_id,
                message_id=post.message_id,
            )
        except Exception:
            logger.exception(
                "broadcast_forward_failed",
                extra={
                    "source_channel_id": source_channel_id,
                    "target_group_id": group_id,
                },
            )
