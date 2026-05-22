from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.decorators import feature_toggle, log_command

MODULE_NAME = "fun"


def _target_name(update: Update) -> str:
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user.full_name
    if update.effective_user:
        return update.effective_user.full_name
    return "crewmate"


@log_command
@feature_toggle("fun")
async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(f"*pat* for {_target_name(update)}.")


@log_command
@feature_toggle("fun")
async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(
            f"Careful now. {_target_name(update)} was slapped."
        )


@log_command
@feature_toggle("fun")
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(
            f"A warm hug for {_target_name(update)}."
        )


def register(application) -> None:
    application.add_handler(CommandHandler("pat", pat))
    application.add_handler(CommandHandler("slap", slap))
    application.add_handler(CommandHandler("hug", hug))
