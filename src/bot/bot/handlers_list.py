from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.bot.bot.plugins import acn_broadcast as acn_broadcast_plugin
from src.bot.bot.plugins import admin as admin_plugin
from src.bot.bot.plugins import ai_mod as ai_mod_plugin
from src.bot.bot.plugins import channel_guard as channel_guard_plugin
from src.bot.bot.plugins import feature_management as feature_management_plugin
from src.bot.bot.plugins import filters as filters_plugin
from src.bot.bot.plugins import flood_control as flood_control_plugin
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
    description: str = ""
    feature_gate: str | None = None
    show_in_main_menu: bool = False
    aliases: tuple[str, ...] = ()


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
    CommandBinding("start", welcome_plugin.start, "DM welcome and bot intro", show_in_main_menu=True),
    CommandBinding("help", welcome_plugin.help_cmd, "Main help message", show_in_main_menu=True),
    CommandBinding("ping", ping, "Alive check", show_in_main_menu=True),
    CommandBinding("management", feature_management_plugin.management_help, "Management command guide", show_in_main_menu=True),

    # ── Features ──
    CommandBinding("features", feature_management_plugin.features, "Feature status", show_in_main_menu=True),

    # ── Moderation ──
    CommandBinding("ban", admin_plugin.ban, "Ban user", "moderation", True),
    CommandBinding("unban", admin_plugin.unban, "Unban user", "moderation", False),
    CommandBinding("kick", admin_plugin.kick, "Kick user", "moderation", False),
    CommandBinding("mute", admin_plugin.mute, "Mute user", "moderation", True),
    CommandBinding("warn", admin_plugin.warn, "Warn user", "moderation", True),

    # ── Filters ──
    CommandBinding("filter", filters_plugin.add_filter, "Add filter", "filters", False),
    CommandBinding("stop", filters_plugin.stop_filter, "Stop filter", "filters", False),
    CommandBinding("filters", filters_plugin.list_filters, "List filters", "filters", True),
    CommandBinding("filteraction", filters_plugin.filter_action, "Set filter action", "filters", False),

    # ── Welcome & Rules ──
    CommandBinding("setwelcome", welcome_plugin.setwelcome, "Set welcome text", "welcome", False),
    CommandBinding("setwelcomedm", welcome_plugin.setwelcomedm, "Set welcome DM", "welcome", False),
    CommandBinding("welcomedm", welcome_plugin.welcomedm_toggle, "Toggle welcome DM", "welcome", False),
    CommandBinding("resetwelcome", welcome_plugin.resetwelcome, "Reset welcome", "welcome", False),
    CommandBinding("welcome", welcome_plugin.welcome_toggle, "Toggle welcome", "welcome", True),
    CommandBinding("setfarewell", welcome_plugin.setfarewell, "Set farewell text", "welcome", False),
    CommandBinding("farewell", welcome_plugin.farewell_toggle, "Toggle farewell", "welcome", False),
    CommandBinding("cleanwelcome", welcome_plugin.cleanwelcome, "Toggle clean welcome", "welcome", False),
    CommandBinding("setrules", welcome_plugin.setrules, "Set rules", "welcome", False),
    CommandBinding("rules", welcome_plugin.rules, "View rules", "welcome", True),
    CommandBinding("welcometest", welcome_plugin.welcometest, "Test welcome", "welcome", False),

    # ── Notes ──
    CommandBinding("save", notes_plugin.save, "Save note", "notes", False),
    CommandBinding("get", notes_plugin.get, "Get note", "notes", False),
    CommandBinding("notes", notes_plugin.notes, "List notes", "notes", True),
    CommandBinding("clear", notes_plugin.clear, "Clear note", "notes", False),

    # ── Locks ──
    CommandBinding("lock", locks_plugin.lock_cmd, "Lock media type", "locks", False),
    CommandBinding("unlock", locks_plugin.unlock_cmd, "Unlock media type", "locks", False),
    CommandBinding("locks", locks_plugin.locks_cmd, "List active locks", "locks", True),

    # ── Flood & AI ──
    CommandBinding("toggleai", ai_mod_plugin.toggleai, "Toggle AI mod", "ai_moderation", False),
    CommandBinding("setflood", flood_control_plugin.setflood, "Set flood limit", "flood_control", False),
    CommandBinding("setfloodmode", flood_control_plugin.setfloodmode, "Set flood mode", "flood_control", False),
    CommandBinding("flood", flood_control_plugin.flood, "Toggle flood control", "flood_control", False),

    # ── Swear Words ──
    CommandBinding("addswear", swear_words_plugin.add_swear_word, "Add swear word", "swear_words", False),
    CommandBinding("delswear", swear_words_plugin.remove_swear_word, "Delete swear word", "swear_words", False),
    CommandBinding("swearlist", swear_words_plugin.list_swear_words, "List swear words", "swear_words", False),
    CommandBinding("swearsettings", swear_words_plugin.swear_settings, "Swear settings", "swear_words", False),

    # ── Broadcast ──
    CommandBinding("broadcastchannels", acn_broadcast_plugin.list_broadcast_channels, "List broadcast channels", "acn_broadcast", False),
    CommandBinding("broadcaststatus", acn_broadcast_plugin.broadcast_status, "Broadcast status", "acn_broadcast", False),
    CommandBinding("testbroadcast", acn_broadcast_plugin.test_broadcast, "Test broadcast", "acn_broadcast", False),
    CommandBinding("broadcasthelp", acn_broadcast_plugin.broadcast_help, "Broadcast help", "acn_broadcast", False),
    CommandBinding("addbroadcast", acn_broadcast_plugin.add_broadcast_channel_cmd, "Add broadcast channel", "acn_broadcast", False),
    CommandBinding("removebroadcast", acn_broadcast_plugin.remove_broadcast_channel_cmd, "Remove broadcast channel", "acn_broadcast", False),
    CommandBinding("addmaingroup", acn_broadcast_plugin.add_main_group_cmd, "Add main ACN group", "acn_broadcast", False),

    # ── Channel Guard ──
    CommandBinding("channelpost", channel_guard_plugin.channel_post_cmd, "Send a message to a channel"),
    CommandBinding("channelphoto", channel_guard_plugin.channel_photo_cmd, "Send a photo to a channel"),
    CommandBinding("addpurgechannel", channel_guard_plugin.add_purge_channel, "Add an auto-purge channel"),
    CommandBinding("removepurgechannel", channel_guard_plugin.remove_purge_channel, "Remove an auto-purge channel"),
    CommandBinding("purgechannels", channel_guard_plugin.list_purge_channels, "List purge channels"),

    # ── Internal ──
    CommandBinding("check_handlers", check_handlers, "Check handlers", show_in_main_menu=False),
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
        commands_to_register = [binding.command] + list(binding.aliases)
        for cmd in commands_to_register:
            cmd_casefold = cmd.casefold()
            if cmd_casefold in existing_commands:
                continue
            application.add_handler(
                CommandHandler(cmd, log_command(binding.callback))
            )
            existing_commands.add(cmd_casefold)
