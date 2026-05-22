from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.bot.bot.plugins import acn_broadcast as acn_broadcast_plugin
from src.bot.bot.plugins import acn_loyalty as acn_loyalty_plugin
from src.bot.bot.plugins import admin as admin_plugin
from src.bot.bot.plugins import ai_mod as ai_mod_plugin
from src.bot.bot.plugins import bot_friendship as bot_friendship_plugin
from src.bot.bot.plugins import captcha as captcha_plugin
from src.bot.bot.plugins import channel_guard as channel_guard_plugin
from src.bot.bot.plugins import federation as federation_plugin
from src.bot.bot.plugins import feature_management as feature_management_plugin
from src.bot.bot.plugins import filters as filters_plugin
from src.bot.bot.plugins import flood_control as flood_control_plugin
from src.bot.bot.plugins import flirting as flirting_plugin
from src.bot.bot.plugins import fun as fun_plugin
from src.bot.bot.plugins import locks as locks_plugin
from src.bot.bot.plugins import nightmode as nightmode_plugin
from src.bot.bot.plugins import notes as notes_plugin
from src.bot.bot.plugins import points as points_plugin
from src.bot.bot.plugins import profile as profile_plugin
from src.bot.bot.plugins import purge as purge_plugin
from src.bot.bot.plugins import scheduler as scheduler_plugin
from src.bot.bot.plugins import settings as settings_plugin
from src.bot.bot.plugins import swear_words as swear_words_plugin
from src.bot.bot.plugins import user_info as user_info_plugin
from src.bot.bot.plugins import welcome as welcome_plugin
from src.bot.bot.plugins import stats as stats_plugin
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
    CommandBinding("start", welcome_plugin.start),
    CommandBinding("help", welcome_plugin.help_cmd),
    CommandBinding("ping", ping),
    CommandBinding("robin", fun_plugin.robin),
    CommandBinding("check_handlers", check_handlers),
    CommandBinding("management", feature_management_plugin.management_help),
    CommandBinding("enable", feature_management_plugin.enable_feature),
    CommandBinding("disable", feature_management_plugin.disable_feature),
    CommandBinding("toggle", feature_management_plugin.toggle_feature),
    CommandBinding("features", feature_management_plugin.features),
    CommandBinding("feature_info", feature_management_plugin.feature_info),
    CommandBinding("feature_logs", feature_management_plugin.feature_logs),
    CommandBinding("feature_stats", feature_management_plugin.feature_stats),
    CommandBinding("my_features", feature_management_plugin.my_features),
    CommandBinding("reset_features", feature_management_plugin.reset_features),
    CommandBinding("enable_category", feature_management_plugin.enable_category),
    CommandBinding(
        "disable_category", feature_management_plugin.disable_category
    ),
    CommandBinding("ban", admin_plugin.ban),
    CommandBinding("unban", admin_plugin.unban),
    CommandBinding("kick", admin_plugin.kick),
    CommandBinding("mute", admin_plugin.mute),
    CommandBinding("unmute", admin_plugin.unmute),
    CommandBinding("warn", admin_plugin.warn),
    CommandBinding("warns", admin_plugin.warns),
    CommandBinding("resetwarn", admin_plugin.resetwarn),
    CommandBinding("pin", admin_plugin.pin),
    CommandBinding("del", admin_plugin.delete_message),
    CommandBinding("slowmode", admin_plugin.slowmode),
    CommandBinding("filter", filters_plugin.add_filter),
    CommandBinding("stop", filters_plugin.stop_filter),
    CommandBinding("filters", filters_plugin.list_filters),
    CommandBinding("filteraction", filters_plugin.filter_action),
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
    CommandBinding("save", notes_plugin.save),
    CommandBinding("get", notes_plugin.get),
    CommandBinding("notes", notes_plugin.notes),
    CommandBinding("clear", notes_plugin.clear),
    CommandBinding("purge", purge_plugin.purge),
    CommandBinding("lock", locks_plugin.lock_cmd),
    CommandBinding("unlock", locks_plugin.unlock_cmd),
    CommandBinding("locks", locks_plugin.locks_cmd),
    CommandBinding("schedule", scheduler_plugin.schedule),
    CommandBinding("stats", stats_plugin.stats),
    CommandBinding("newfed", federation_plugin.newfed),
    CommandBinding("joinfed", federation_plugin.joinfed),
    CommandBinding("captcha", captcha_plugin.captcha),
    CommandBinding("toggleai", ai_mod_plugin.toggleai),
    CommandBinding("setflood", flood_control_plugin.setflood),
    CommandBinding("setfloodmode", flood_control_plugin.setfloodmode),
    CommandBinding("flood", flood_control_plugin.flood),
    CommandBinding("points", points_plugin.points),
    CommandBinding("leaderboard", points_plugin.leaderboard),
    CommandBinding("award", points_plugin.award_points),
    CommandBinding("recalculate_points", points_plugin.recalculate_points),
    CommandBinding("apploids", points_plugin.apploids),
    CommandBinding("buy_apploid", points_plugin.buy_apploid),
    CommandBinding("equip_apploid", points_plugin.equip_apploid),
    CommandBinding("point_stats", points_plugin.point_stats),
    CommandBinding("earn_points", points_plugin.earn_points),
    CommandBinding("point_help", points_plugin.point_help),
    CommandBinding("profile", profile_plugin.profile_command),
    CommandBinding("setbio", profile_plugin.setbio_command),
    CommandBinding("id", user_info_plugin.id_command),
    CommandBinding("whois", user_info_plugin.whois),
    CommandBinding("info", user_info_plugin.whois),
    CommandBinding("addswear", swear_words_plugin.add_swear_word),
    CommandBinding("delswear", swear_words_plugin.remove_swear_word),
    CommandBinding("swearlist", swear_words_plugin.list_swear_words),
    CommandBinding("swearsettings", swear_words_plugin.swear_settings),
    CommandBinding(
        "broadcastchannels", acn_broadcast_plugin.list_broadcast_channels
    ),
    CommandBinding("broadcaststatus", acn_broadcast_plugin.broadcast_status),
    CommandBinding("testbroadcast", acn_broadcast_plugin.test_broadcast),
    CommandBinding("broadcasthelp", acn_broadcast_plugin.broadcast_help),
    CommandBinding(
        "addbroadcast", acn_broadcast_plugin.add_broadcast_channel_cmd
    ),
    CommandBinding(
        "removebroadcast", acn_broadcast_plugin.remove_broadcast_channel_cmd
    ),
    CommandBinding("addmaingroup", acn_broadcast_plugin.add_main_group_cmd),
    CommandBinding("channelpost", channel_guard_plugin.channel_post_cmd),
    CommandBinding("channelphoto", channel_guard_plugin.channel_photo_cmd),
    CommandBinding(
        "addpurgechannel", channel_guard_plugin.add_purge_channel
    ),
    CommandBinding(
        "removepurgechannel", channel_guard_plugin.remove_purge_channel
    ),
    CommandBinding(
        "purgechannels", channel_guard_plugin.list_purge_channels
    ),
    CommandBinding("acn_status", acn_loyalty_plugin.acn_status),
    CommandBinding(
        "loyalty_leaderboard", acn_loyalty_plugin.loyalty_leaderboard
    ),
    CommandBinding("addacngroup", acn_loyalty_plugin.add_acn_group),
    CommandBinding("addacn", acn_loyalty_plugin.add_acn_member),
    CommandBinding("removeacn", acn_loyalty_plugin.remove_acn_member),
    CommandBinding("acn_members", acn_loyalty_plugin.acn_members),
    CommandBinding("acn_info", acn_loyalty_plugin.acn_info),
    CommandBinding("flirt", flirting_plugin.flirt),
    CommandBinding("flirt_stats", flirting_plugin.flirt_stats),
    CommandBinding("flirt_categories", flirting_plugin.flirt_categories),
    CommandBinding("flirt_achievements", flirting_plugin.flirt_achievements),
    CommandBinding("flirt_help", flirting_plugin.flirt_help),
    CommandBinding("flirt_example", flirting_plugin.flirt_example),
    CommandBinding("flirt_random", flirting_plugin.flirt_random),
    CommandBinding("bond_with_yamato", bot_friendship_plugin.bond_with_yamato),
    CommandBinding("yamato_interact", bot_friendship_plugin.yamato_interact),
    CommandBinding("yamato_status", bot_friendship_plugin.yamato_status),
    CommandBinding("yamato_memories", bot_friendship_plugin.yamato_memories),
    CommandBinding("gift_to_yamato", bot_friendship_plugin.gift_to_yamato),
    CommandBinding(
        "yamato_activities", bot_friendship_plugin.yamato_activities
    ),
    CommandBinding("yamato_help", bot_friendship_plugin.yamato_help),
    CommandBinding("nightmode", nightmode_plugin.nightmode),
    CommandBinding("setlocale", settings_plugin.setlocale),
    CommandBinding("setwarnlimit", settings_plugin.setwarnlimit),
    CommandBinding("setwarnaction", settings_plugin.setwarnaction),
    CommandBinding("setlogchannel", settings_plugin.setlogchannel),
    CommandBinding("removelogchannel", settings_plugin.removelogchannel),
)


def register_command_handlers(application: Application) -> None:
    for binding in COMMAND_BINDINGS:
        application.add_handler(
            CommandHandler(binding.command, log_command(binding.callback))
        )
