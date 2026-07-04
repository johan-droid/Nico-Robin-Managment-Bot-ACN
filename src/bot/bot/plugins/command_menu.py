from telegram import Update
from telegram.ext import ContextTypes

from src.bot.bot.handlers_list import COMMAND_BINDINGS, _reply_in_chunks


async def allcommands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return

    lines = ["📚 **All Available Commands:**\n"]
    for binding in COMMAND_BINDINGS:
        desc = f" - {binding.description}" if binding.description else ""
        lines.append(f"/{binding.command}{desc}")

    await _reply_in_chunks(msg, "\n".join(lines))


def register(app):
    pass
