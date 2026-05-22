from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters as tg_filters

from core.decorators import feature_toggle, get_runtime, log_command

MODULE_NAME = "filters"


@feature_toggle("filters")
@log_command
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if len(args) < 2:
        await message.reply_text("🌸 Usage: /filter <pattern> <response>")
        return
    pattern = args[0].lower().strip()
    response = " ".join(args[1:]).strip()
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO filters (group_id, pattern, action, response, created_by)
        VALUES (?, ?, 'reply', ?, ?)
        ON CONFLICT(group_id, pattern) DO UPDATE SET response = excluded.response, updated_at = CURRENT_TIMESTAMP
        """,
        (chat.id, pattern, response, update.effective_user.id if update.effective_user else None),
    )
    await message.reply_text(f"🌸 Filter saved for '{pattern}'.")


@feature_toggle("filters")
@log_command
async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /stop <pattern>")
        return
    db = get_runtime(context)["db"]
    await db.execute("DELETE FROM filters WHERE group_id = ? AND pattern = ?", (chat.id, args[0].lower().strip()))
    await message.reply_text("🌸 Filter removed.")


@feature_toggle("filters")
@log_command
async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    db = get_runtime(context)["db"]
    rows = await db.fetchall("SELECT pattern, response FROM filters WHERE group_id = ? ORDER BY pattern", (chat.id,))
    if not rows:
        await message.reply_text("🌸 No filters configured.")
        return
    await message.reply_text("🌸 Filters:\n" + "\n".join(f"• {row[0]} -> {row[1]}" for row in rows))


@feature_toggle("filters")
@log_command
async def filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("🌸 Usage: /filteraction <delete|reply>")
        return
    action = args[0].lower().strip()
    if action not in {"delete", "reply"}:
        await message.reply_text("🌸 Action must be delete or reply.")
        return
    db = get_runtime(context)["db"]
    await db.execute(
        """
        INSERT INTO group_settings (group_id, welcome_enabled, farewell_enabled, clean_welcome, updated_at)
        VALUES (?, COALESCE((SELECT welcome_enabled FROM group_settings WHERE group_id = ?), 1), COALESCE((SELECT farewell_enabled FROM group_settings WHERE group_id = ?), 1), COALESCE((SELECT clean_welcome FROM group_settings WHERE group_id = ?), 0), CURRENT_TIMESTAMP)
        ON CONFLICT(group_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
        """,
        (chat.id, chat.id, chat.id, chat.id),
    )
    await db.execute("UPDATE filters SET action = ? WHERE group_id = ?", (action, chat.id))
    await message.reply_text(f"🌸 Filter action set to {action}.")


@feature_toggle("filters")
async def filter_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None or not message.text:
        return
    db = get_runtime(context)["db"]
    rows = await db.fetchall("SELECT pattern, action, response FROM filters WHERE group_id = ?", (chat.id,))
    text = message.text.lower()
    for pattern, action, response in rows:
        if pattern in text:
            if action == "delete":
                await message.delete()
            else:
                await message.reply_text(response or "🌸 Message matched a filter.")
            return


def register(application) -> None:
    application.add_handler(CommandHandler("filter", add_filter, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("stop", stop_filter, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("filters", list_filters, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("filteraction", filter_action, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(MessageHandler(tg_filters.ChatType.GROUPS & tg_filters.TEXT & ~tg_filters.COMMAND, filter_message), group=0)
