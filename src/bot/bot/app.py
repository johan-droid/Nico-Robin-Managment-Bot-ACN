"""Bot application factory — with all security layers registered."""

from __future__ import annotations

import structlog
from telegram.ext import Application, MessageHandler, TypeHandler
from telegram.ext import filters as tg_filters

from src.bot.bot.dispatcher import register_all_handlers
from src.bot.bot.middleware.command_guard import command_input_guard
from src.bot.bot.middleware.error_handler import global_error_handler
from src.bot.bot.middleware.feature_gate import feature_gate_check
from src.bot.bot.middleware.group_guard import (
    _StopProcessing,
    group_guard,
    group_guard_error_handler,
)
from src.bot.bot.middleware.message_tracker import track_message
from src.bot.bot.middleware.request_logger import log_update_details
from src.bot.bot.middleware.security import rate_limit_check
from src.bot.config import Settings, settings

logger = structlog.get_logger(__name__)


async def _rate_limit_gate(update, context) -> None:
    """Rate limiting gate. Blocks abusive users before plugin handlers run."""
    try:
        blocked = await rate_limit_check(update, context)
        if blocked:
            raise _StopProcessing()
        await command_input_guard(update, context)
        await feature_gate_check(update, context)
    except _StopProcessing:
        raise
    except Exception as exc:
        logger.error(
            "middleware_crash",
            error=str(exc)[:500],
            error_type=type(exc).__name__,
        )
        raise


def create_application(app_settings: Settings = settings) -> Application:
    # In polling mode (no webhook), use the default updater to fetch updates
    # In webhook mode, disable updater since updates come via HTTP
    builder = Application.builder().token(app_settings.bot_token)

    # Only disable updater if using webhook mode
    if app_settings.is_webhook_mode:
        builder = builder.updater(None)

    application = builder.build()

    # PTB processes handler groups in ascending order: -3 → -2 → -1 → 0 → 1 ...
    # group=-3: Request logger — logs ALL updates first for complete visibility
    application.add_handler(
        TypeHandler(type=object, callback=log_update_details), group=-3
    )

    # group=-2: Group guard — blocks unauthorized groups
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
