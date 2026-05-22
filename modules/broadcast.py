from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import log_command, require_commander_or_captain

MODULE_NAME = "broadcast"


def _parse_id(raw: str) -> int | None:
    cleaned = raw.strip()
    if cleaned.lstrip("-").isdigit():
        return int(cleaned)
    return None


@log_command
@require_commander_or_captain
async def addbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /addbroadcast <channel_id>")
        return
    channel_id = _parse_id(context.args[0])
    if channel_id is None:
        await msg.reply_text("Channel id must be numeric.")
        return
    db = context.application.bot_data["db"]
    await db.execute(
        """
        INSERT INTO broadcast_sources (channel_id, channel_name, is_active)
        VALUES (?, ?, 1)
        ON CONFLICT(channel_id)
        DO UPDATE SET is_active = 1
        """,
        (channel_id, context.args[1] if len(context.args) > 1 else None),
    )
    await msg.reply_text(f"Broadcast source {channel_id} added.")


@log_command
@require_commander_or_captain
async def removebroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /removebroadcast <channel_id>")
        return
    channel_id = _parse_id(context.args[0])
    if channel_id is None:
        await msg.reply_text("Channel id must be numeric.")
        return
    db = context.application.bot_data["db"]
    await db.execute(
        "UPDATE broadcast_sources SET is_active = 0 WHERE channel_id = ?",
        (channel_id,),
    )
    await msg.reply_text(f"Broadcast source {channel_id} disabled.")


@log_command
@require_commander_or_captain
async def addmaingroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    db = context.application.bot_data["db"]
    await db.execute(
        """
        INSERT INTO broadcast_targets (group_id, group_name, is_active)
        VALUES (?, ?, 1)
        ON CONFLICT(group_id)
        DO UPDATE SET group_name = excluded.group_name, is_active = 1
        """,
        (chat.id, chat.title),
    )
    await msg.reply_text("This group is now an active broadcast target.")


def register(application) -> None:
    application.add_handler(CommandHandler("addbroadcast", addbroadcast))
    application.add_handler(CommandHandler("removebroadcast", removebroadcast))
    application.add_handler(CommandHandler("addmaingroup", addmaingroup))
