from __future__ import annotations

from collections.abc import Callable
from importlib import import_module

import structlog
from telegram.ext import Application, CommandHandler

from bot.plugins.fun import robin

logger = structlog.get_logger(__name__)

PLUGIN_MODULES: tuple[str, ...] = (
    "bot.plugins.admin",
    "bot.plugins.filters",
    "bot.plugins.welcome",
    "bot.plugins.notes",
    "bot.plugins.purge",
    "bot.plugins.captcha",
    "bot.plugins.federation",
    "bot.plugins.stats",
    "bot.plugins.user_info",
    "bot.plugins.settings",
    "bot.plugins.flood_control",
    "bot.plugins.ai_mod",
    "bot.plugins.swear_words",
    "bot.plugins.nico_moments",
    "bot.plugins.acn_loyalty",
    "bot.plugins.acn_broadcast",
    "bot.plugins.flirting",
    "bot.plugins.feature_management",
    "bot.plugins.bot_friendship",
    "bot.plugins.points",
    "bot.plugins.channel_guard",
    "bot.plugins.profile",
    "bot.plugins.nightmode",
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
