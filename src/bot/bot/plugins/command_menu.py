from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.bot.handlers_list import COMMAND_BINDINGS, _reply_in_chunks


async def allcommands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return

    lines = ["📚 **All Available Commands:**\n"]
    for binding in COMMAND_BINDINGS:
        lines.append(
            f"/{binding.command} - `{binding.callback.__module__.rsplit('.', 1)[-1]}`"
        )

    await _reply_in_chunks(msg, "\n".join(lines))


def register(app):
    app.add_handler(CommandHandler(["commands", "allcommands"], allcommands))
