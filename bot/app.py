"""Bot application factory — with all security layers registered."""

from __future__ import annotations

from telegram.ext import Application, MessageHandler, TypeHandler
from telegram.ext import filters as tg_filters

from bot.dispatcher import register_all_handlers
from bot.middleware.error_handler import global_error_handler
from bot.middleware.group_guard import (
    _StopProcessing,
    group_guard,
    group_guard_error_handler,
)
from bot.middleware.message_tracker import track_message
from bot.middleware.security import rate_limit_check
from config import Settings, settings


async def _rate_limit_gate(update, context) -> None:
    """Rate limiting gate. Blocks abusive users before plugin handlers run."""
    if await rate_limit_check(update, context):
        raise _StopProcessing()


def create_application(app_settings: Settings = settings) -> Application:
    application = Application.builder().token(app_settings.bot_token).build()

    # PTB processes handler groups in ascending order: -2 → -1 → 0 → 1 ...
    # group=-2: Group guard — blocks unauthorized groups first
    application.add_handler(TypeHandler(type=object, callback=group_guard), group=-2)

    # group=-1: Rate limiter — blocks abusive users after group check
    application.add_handler(
        TypeHandler(type=object, callback=_rate_limit_gate), group=-1
    )

    # Error handlers (order matters — first registered gets first chance)
    application.add_error_handler(group_guard_error_handler)
    application.add_error_handler(global_error_handler)

    # group=0: All plugin handlers
    register_all_handlers(application)

    # group=1: Message tracker — passive, runs AFTER plugins, never blocks
    application.add_handler(
        MessageHandler(tg_filters.ALL, track_message),
        group=1,
    )

    return application
