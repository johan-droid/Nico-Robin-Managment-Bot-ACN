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
from bot.middleware.request_logger import log_update_details
from bot.middleware.security import rate_limit_check
from config import Settings, settings


async def _rate_limit_gate(update, context) -> None:
    """Rate limiting gate. Blocks abusive users before plugin handlers run."""
    try:
        blocked = await rate_limit_check(update, context)
        if blocked:
            raise _StopProcessing()
    except _StopProcessing:
        raise
    except Exception:
        # Prevent leaking tracebacks if rate limiter itself crashes
        pass


def create_application(app_settings: Settings = settings) -> Application:
    # In polling mode (no webhook), use the default updater to fetch updates
    # In webhook mode, disable updater since updates come via HTTP
    builder = Application.builder().token(app_settings.bot_token)

    # Only disable updater if using webhook mode
    if app_settings.webhook_url and app_settings.webhook_url.startswith("https://"):
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
