from __future__ import annotations

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CommandHandler, ContextTypes

from src.bot.utils.decorators import admin_only, bot_rights_required, group_only


@group_only
@admin_only
@bot_rights_required("can_delete_messages")
async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    if msg.reply_to_message:
        start = msg.reply_to_message.message_id
        end = msg.message_id
    else:
        try:
            count = max(1, min(int((context.args or ["10"])[0]), 100))
        except ValueError:
            count = 10
        start = msg.message_id - count
        end = msg.message_id
    deleted = 0
    for message_id in range(start, end + 1):
        try:
            await context.bot.delete_message(chat.id, message_id)
            deleted += 1
        except TelegramError:
            continue
    notice = await context.bot.send_message(
        chat.id,
        f"🌸 Purged {deleted} pages from the archive.",
    )
    try:
        await notice.delete()
    except TelegramError:
        pass


def register(app) -> None:
    app.add_handler(CommandHandler("purge", purge))
