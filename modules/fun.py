from __future__ import annotations

import random

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters as tg_filters

from core.decorators import log_command

MODULE_NAME = "fun"
RESPONSES = {
    "pat": ["🌸 Robin pats you gently.", "🌸 A calm pat, delivered with precision."],
    "slap": ["🌸 Robin delivers a reality check.", "🌸 That was a decisive slap."],
    "hug": ["🌸 Robin gives a warm hug.", "🌸 A thoughtful hug, steady and kind."],
}


async def _reply(update: Update, key: str) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(random.choice(RESPONSES[key]))


@log_command
async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "pat")


@log_command
async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "slap")


@log_command
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "hug")


def register(application) -> None:
    application.add_handler(CommandHandler("pat", pat, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("slap", slap, filters=tg_filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("hug", hug, filters=tg_filters.ChatType.GROUPS))
