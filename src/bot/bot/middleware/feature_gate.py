from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.services.feature_service import FeatureService

COMMAND_FEATURES: dict[str, str] = {
    "ban": "moderation",
    "unban": "moderation",
    "kick": "moderation",
    "mute": "moderation",
    "unmute": "moderation",
    "warn": "moderation",
    "warns": "moderation",
    "resetwarn": "moderation",
    "slowmode": "moderation",
    "del": "moderation",
    "pin": "moderation",
    "filter": "filters",
    "stop": "filters",
    "filters": "filters",
    "filteraction": "filters",
    "setwelcome": "welcome",
    "resetwelcome": "welcome",
    "welcome": "welcome",
    "setfarewell": "welcome",
    "farewell": "welcome",
    "cleanwelcome": "welcome",
    "welcometest": "welcome",
    "save": "notes",
    "get": "notes",
    "notes": "notes",
    "clear": "notes",
    "purge": "purge",
    "schedule": "scheduler",
    "captcha": "captcha",
    "newfed": "federation",
    "joinfed": "federation",
    "addbroadcast": "acn_broadcast",
    "removebroadcast": "acn_broadcast",
    "broadcastchannels": "acn_broadcast",
    "broadcaststatus": "acn_broadcast",
    "broadcasthelp": "acn_broadcast",
    "testbroadcast": "acn_broadcast",
    "flirt": "flirting",
    "flirt_stats": "flirting",
    "flirt_categories": "flirting",
    "flirt_achievements": "flirting",
    "flirt_example": "flirting",
    "points": "points",
    "leaderboard": "points",
    "apploids": "points",
    "buy_apploid": "points",
    "equip_apploid": "points",
    "point_stats": "points",
    "earn_points": "points",
    "point_help": "points",
    "profile": "profile",
    "setbio": "profile",
    "toggleai": "security",
    "setflood": "security",
    "setfloodmode": "security",
    "flood": "security",
    "addswear": "security",
    "delswear": "security",
    "swearlist": "security",
    "swearsettings": "security",
    "export_my_data": "profile",
    "delete_my_data": "profile",
    "clear_user_data": "security",
}


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
        chat.id, feature_name, user.id
    )
    if can_use:
        return
    await message.reply_text(f"🚫 {reason}")
    raise RuntimeError("_feature_blocked")
