from __future__ import annotations

from collections.abc import Callable
from importlib import import_module

import structlog
from telegram.ext import Application, CommandHandler

from src.bot.bot.plugins.fun import robin

logger = structlog.get_logger(__name__)

PLUGIN_MODULES: tuple[str, ...] = (
    "src.bot.bot.plugins.admin",
    "src.bot.bot.plugins.filters",
    "src.bot.bot.plugins.welcome",
    "src.bot.bot.plugins.notes",
    "src.bot.bot.plugins.locks",
    "src.bot.bot.plugins.scheduler",
    "src.bot.bot.plugins.purge",
    "src.bot.bot.plugins.captcha",
    "src.bot.bot.plugins.federation",
    "src.bot.bot.plugins.stats",
    "src.bot.bot.plugins.user_info",
    "src.bot.bot.plugins.settings",
    "src.bot.bot.plugins.flood_control",
    "src.bot.bot.plugins.ai_mod",
    "src.bot.bot.plugins.swear_words",
    "src.bot.bot.plugins.nico_moments",
    "src.bot.bot.plugins.acn_loyalty",
    "src.bot.bot.plugins.acn_broadcast",
    "src.bot.bot.plugins.flirting",
    "src.bot.bot.plugins.feature_management",
    "src.bot.bot.plugins.bot_friendship",
    "src.bot.bot.plugins.points",
    "src.bot.bot.plugins.channel_guard",
    "src.bot.bot.plugins.profile",
    "src.bot.bot.plugins.nightmode",
    "src.bot.bot.plugins.locks",
    "src.bot.bot.plugins.scheduler",
)


async def ping(update, context) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(
            "🌸 Pong. The archive is awake, and the record is intact."
        )


def register_all_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("robin", robin))

    for module_name in PLUGIN_MODULES:
        module = import_module(module_name)
        register: Callable[[Application], None] | None = getattr(
            module, "register", None
        )
        if register is None:
            logger.warning("plugin_missing_register", module=module_name)
            continue
        register(application)
        logger.info("plugin_registered", module=module_name)
