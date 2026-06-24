from __future__ import annotations

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from src.bot.bot.handlers_list import COMMAND_BINDINGS
from src.bot.services.feature_service import FeatureService

# Build mapping dynamically
COMMAND_FEATURES: dict[str, str] = {}
for binding in COMMAND_BINDINGS:
    if binding.feature_gate:
        COMMAND_FEATURES[binding.command.casefold()] = binding.feature_gate
        for alias in binding.aliases:
            COMMAND_FEATURES[alias.casefold()] = binding.feature_gate


async def feature_gate_check(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not isinstance(update, Update):
        return
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None or not message.text:
        return
    if not message.text.startswith("/"):
        return
    command = message.text.split()[0].split("@")[0].removeprefix("/").lower()
    feature_name = COMMAND_FEATURES.get(command)
    if feature_name is None:
        return
    can_use, reason = await FeatureService.can_use_feature(
        chat.id, feature_name, user.id, chat=chat, context=context
    )
    if can_use:
        return
    await message.reply_text(f"🚫 {reason}")
    raise ApplicationHandlerStop()
