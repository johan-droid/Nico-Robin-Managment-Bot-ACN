from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.services.security_logger import SecurityLogger
from src.bot.utils.sanitizer import contains_dangerous_input, sanitize_args


async def command_input_guard(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not isinstance(update, Update):
        return
    message = update.effective_message
    if message is None or not message.text or not message.text.startswith("/"):
        return
    if context.args:
        original_args = list(context.args)
        combined = " ".join(original_args)
        if contains_dangerous_input(combined):
            await SecurityLogger.log_event(
                event_type="command_input_blocked",
                user_id=update.effective_user.id if update.effective_user else None,
                chat_id=update.effective_chat.id if update.effective_chat else None,
                severity="HIGH",
                details={"command": message.text.split()[0], "input": combined[:200]},
            )
            await message.reply_text("🛡️ Suspicious input detected and blocked.")
            raise RuntimeError("_command_blocked")
        context._args = sanitize_args(original_args)  # noqa: SLF001
