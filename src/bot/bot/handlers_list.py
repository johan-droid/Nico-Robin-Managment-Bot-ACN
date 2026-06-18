from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.bot.bot.plugins import acn_broadcast as acn_broadcast_plugin
from src.bot.bot.plugins import ai_mod as ai_mod_plugin
from src.bot.bot.plugins import channel_guard as channel_guard_plugin
from src.bot.bot.plugins import filters as filters_plugin
from src.bot.bot.plugins import flood_control as flood_control_plugin
from src.bot.bot.plugins import fun as fun_plugin
from src.bot.bot.plugins import locks as locks_plugin
from src.bot.bot.plugins import notes as notes_plugin
from src.bot.bot.plugins import swear_words as swear_words_plugin
from src.bot.bot.plugins import welcome as welcome_plugin
from src.bot.utils.decorators import log_command

CommandCallback = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


@dataclass(frozen=True)
class CommandBinding:
    command: str
    callback: CommandCallback


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(
            "🌸 Pong. The archive is awake, and the record is intact."
        )


def _callback_label(callback: CommandCallback) -> str:
    module_name = callback.__module__.rsplit(".", 1)[-1]
    return f"{module_name}.{callback.__name__}"


def command_handler_lines() -> list[str]:
    return [
        f"/{binding.command} -> {_callback_label(binding.callback)}"
        for binding in COMMAND_BINDINGS
    ]


async def check_handlers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.effective_message
    if msg is None:
        return

    lines = ["Registered command handlers:"]
    lines.extend(command_handler_lines())
    await _reply_in_chunks(msg, "\n".join(lines))


async def _reply_in_chunks(message, text: str, limit: int = 3500) -> None:
    if len(text) <= limit:
        await message.reply_text(text)
        return

    chunk: list[str] = []
    chunk_size = 0
    for line in text.splitlines():
        line_size = len(line) + 1
        if chunk and chunk_size + line_size > limit:
            await message.reply_text("\n".join(chunk))
            chunk = [line]
            chunk_size = line_size
            continue
        chunk.append(line)
        chunk_size += line_size

    if chunk:
        await message.reply_text("\n".join(chunk))


COMMAND_BINDINGS: tuple[CommandBinding, ...] = (
    # ── Core ──
    CommandBinding("start", welcome_plugin.start),
    CommandBinding("help", welcome_plugin.help_cmd),
    CommandBinding("ping", ping),
    CommandBinding("robin", fun_plugin.robin),
    CommandBinding("check_handlers", check_handlers),
    # ── Filters ──
    CommandBinding("filter", filters_plugin.add_filter),
    CommandBinding("stop", filters_plugin.stop_filter),
    CommandBinding("filters", filters_plugin.list_filters),
    CommandBinding("filteraction", filters_plugin.filter_action),
    # ── Welcome & Rules ──
    CommandBinding("setwelcome", welcome_plugin.setwelcome),
    CommandBinding("setwelcomedm", welcome_plugin.setwelcomedm),
    CommandBinding("welcomedm", welcome_plugin.welcomedm_toggle),
    CommandBinding("resetwelcome", welcome_plugin.resetwelcome),
    CommandBinding("welcome", welcome_plugin.welcome_toggle),
    CommandBinding("setfarewell", welcome_plugin.setfarewell),
    CommandBinding("farewell", welcome_plugin.farewell_toggle),
    CommandBinding("cleanwelcome", welcome_plugin.cleanwelcome),
    CommandBinding("setrules", welcome_plugin.setrules),
    CommandBinding("rules", welcome_plugin.rules),
    CommandBinding("welcometest", welcome_plugin.welcometest),
    # ── Notes ──
    CommandBinding("save", notes_plugin.save),
    CommandBinding("get", notes_plugin.get),
    CommandBinding("notes", notes_plugin.notes),
    CommandBinding("clear", notes_plugin.clear),
    # ── Locks ──
    CommandBinding("lock", locks_plugin.lock_cmd),
    CommandBinding("unlock", locks_plugin.unlock_cmd),
    CommandBinding("locks", locks_plugin.locks_cmd),
    # ── Flood & AI ──
    CommandBinding("toggleai", ai_mod_plugin.toggleai),
    CommandBinding("setflood", flood_control_plugin.setflood),
    CommandBinding("setfloodmode", flood_control_plugin.setfloodmode),
    CommandBinding("flood", flood_control_plugin.flood),
    # ── Swear Words ──
    CommandBinding("addswear", swear_words_plugin.add_swear_word),
    CommandBinding("delswear", swear_words_plugin.remove_swear_word),
    CommandBinding("swearlist", swear_words_plugin.list_swear_words),
    CommandBinding("swearsettings", swear_words_plugin.swear_settings),
    # ── Broadcast ──
    CommandBinding("broadcastchannels", acn_broadcast_plugin.list_broadcast_channels),
    CommandBinding("broadcaststatus", acn_broadcast_plugin.broadcast_status),
    CommandBinding("testbroadcast", acn_broadcast_plugin.test_broadcast),
    CommandBinding("broadcasthelp", acn_broadcast_plugin.broadcast_help),
    CommandBinding("addbroadcast", acn_broadcast_plugin.add_broadcast_channel_cmd),
    CommandBinding(
        "removebroadcast", acn_broadcast_plugin.remove_broadcast_channel_cmd
    ),
    CommandBinding("addmaingroup", acn_broadcast_plugin.add_main_group_cmd),
    # ── Channel Guard ──
    CommandBinding("channelpost", channel_guard_plugin.channel_post_cmd),
    CommandBinding("channelphoto", channel_guard_plugin.channel_photo_cmd),
    CommandBinding("addpurgechannel", channel_guard_plugin.add_purge_channel),
    CommandBinding("removepurgechannel", channel_guard_plugin.remove_purge_channel),
    CommandBinding("purgechannels", channel_guard_plugin.list_purge_channels),
)


def register_command_handlers(application: Application) -> None:
    existing_commands = {
        command.casefold()
        for handlers in application.handlers.values()
        for handler in handlers
        if isinstance(handler, CommandHandler)
        for command in handler.commands
    }

    for binding in COMMAND_BINDINGS:
        command_name = binding.command.casefold()
        if command_name in existing_commands:
            continue
        application.add_handler(
            CommandHandler(binding.command, log_command(binding.callback))
        )
        existing_commands.add(command_name)
