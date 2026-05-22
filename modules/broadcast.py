from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters as tg_filters

from core.broadcast_handler import handle_channel_post, handle_edited_channel_post
from core.decorators import get_runtime, log_command, require_commander_or_captain

MODULE_NAME = "broadcast"


@require_commander_or_captain
@log_command
async def addbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    args = context.args or []
    if len(args) < 3:
        await message.reply_text("🌸 Usage: /addbroadcast source|target <id> <name>")
        return
    kind = args[0].lower().strip()
    entity_id = int(args[1])
    name = " ".join(args[2:])
    db = get_runtime(context)["db"]
    if kind == "source":
        await db.execute(
            "INSERT OR REPLACE INTO broadcast_sources (channel_id, channel_name, is_active) VALUES (?, ?, 1)",
            (entity_id, name),
        )
    elif kind == "target":
        await db.execute(
            "INSERT OR REPLACE INTO broadcast_targets (group_id, group_name, is_active) VALUES (?, ?, 1)",
            (entity_id, name),
        )
    else:
        await message.reply_text("🌸 Kind must be source or target.")
        return
    await message.reply_text(f"🌸 Broadcast {kind} saved for {entity_id}.")


@require_commander_or_captain
@log_command
async def removebroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    args = context.args or []
    if len(args) < 2:
        await message.reply_text("🌸 Usage: /removebroadcast source|target <id>")
        return
    kind = args[0].lower().strip()
    entity_id = int(args[1])
    db = get_runtime(context)["db"]
    if kind == "source":
        await db.execute("DELETE FROM broadcast_sources WHERE channel_id = ?", (entity_id,))
    elif kind == "target":
        await db.execute("DELETE FROM broadcast_targets WHERE group_id = ?", (entity_id,))
    else:
        await message.reply_text("🌸 Kind must be source or target.")
        return
    await message.reply_text(f"🌸 Broadcast {kind} removed for {entity_id}.")


def register(application) -> None:
    application.add_handler(CommandHandler("addbroadcast", addbroadcast, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("removebroadcast", removebroadcast, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(MessageHandler(tg_filters.UpdateType.CHANNEL_POST, handle_channel_post))
    application.add_handler(MessageHandler(tg_filters.UpdateType.EDITED_CHANNEL_POST, handle_edited_channel_post))
