from __future__ import annotations

from collections.abc import Callable

import structlog
from telegram.ext import Application

from src.bot.bot.handlers_list import register_command_handlers
from src.bot.bot.plugins.acn_broadcast import register as register_acn_broadcast
from src.bot.bot.plugins.ai_mod import register as register_ai_mod
from src.bot.bot.plugins.channel_guard import register as register_channel_guard
from src.bot.bot.plugins.filters import register as register_filters
from src.bot.bot.plugins.flood_control import register as register_flood_control
from src.bot.bot.plugins.locks import register as register_locks
from src.bot.bot.plugins.notes import register as register_notes
from src.bot.bot.plugins.swear_words import register as register_swear_words
from src.bot.bot.plugins.welcome import register as register_welcome

logger = structlog.get_logger(__name__)

PASSIVE_REGISTERERS: tuple[Callable[[Application], None], ...] = (
    register_welcome,
    register_filters,
    register_notes,
    register_locks,
    register_ai_mod,
    register_flood_control,
    register_swear_words,
    register_acn_broadcast,
    register_channel_guard,
)


def register_all_handlers(application: Application) -> None:
    register_command_handlers(application)

    for register in PASSIVE_REGISTERERS:
        register(application)
        logger.info("plugin_registered", module=register.__module__)
