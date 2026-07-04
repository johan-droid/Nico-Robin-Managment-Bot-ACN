from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.database import async_session_factory
from src.bot.services.warn_service import WarnService
from src.bot.utils.decorators import group_only
from src.bot.utils.formatters import telegram_user_label


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None:
        return
    target = msg.reply_to_message.from_user if msg.reply_to_message else user
    lines = []
    if chat:
        lines.append(f"Chat ID: {chat.id}")
    if target:
        lines.append(f"User ID: {target.id}")
    await msg.reply_text("🌸 " + "\n".join(lines))


@group_only
async def whois(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    target = (
        msg.reply_to_message.from_user
        if msg.reply_to_message
        else update.effective_user
    )
    if target is None:
        return
    async with async_session_factory() as session:
        warns = await WarnService.active_warn_count(session, chat.id, target.id)
    await msg.reply_text(
        f"🌸 {telegram_user_label(target)}\nWarnings: {warns}\nRecord status: readable."
    )


def register(app) -> None:
    pass
