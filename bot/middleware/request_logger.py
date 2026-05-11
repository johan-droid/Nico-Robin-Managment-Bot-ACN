"""Detailed request/update logging middleware for backend visibility."""

from __future__ import annotations

import time

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from utils.logging import bind_update_context

logger = structlog.get_logger(__name__)


async def log_update_details(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Log comprehensive details about every update received."""
    start_time = time.time()

    try:
        # Extract update details
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message

        update_type = None
        message_type = None

        if update.message:
            update_type = "message"
            message_type = "text" if message.text else "media"
        elif update.callback_query:
            update_type = "callback_query"
        elif update.inline_query:
            update_type = "inline_query"
        elif update.chosen_inline_result:
            update_type = "chosen_inline_result"
        elif update.my_chat_member:
            update_type = "my_chat_member"
        else:
            update_type = type(update).__name__

        # Bind context for all logs in this update cycle
        bind_update_context(
            update_id=update.update_id,
            update_type=update_type,
            user_id=user.id if user else None,
            username=f"@{user.username}" if user and user.username else None,
            chat_id=chat.id if chat else None,
            chat_type=chat.type if chat else None,
            chat_title=chat.title if chat and chat.title else None,
            message_id=message.message_id if message else None,
            message_type=message_type,
        )

        # Log incoming update
        log_data = {
            "event": "update_received",
            "update_id": update.update_id,
            "update_type": update_type,
        }

        if user:
            log_data.update(
                {
                    "user_id": user.id,
                    "username": f"@{user.username}" if user.username else None,
                    "user_is_bot": user.is_bot,
                    "user_first_name": user.first_name,
                }
            )

        if chat:
            log_data.update(
                {
                    "chat_id": chat.id,
                    "chat_type": chat.type,
                    "chat_title": chat.title,
                }
            )

        if message:
            log_data.update(
                {
                    "message_id": message.message_id,
                    "message_text": message.text[:100] if message.text else None,
                    "message_type": message_type,
                    "message_date": message.date.isoformat() if message.date else None,
                }
            )

        if update.callback_query:
            log_data.update(
                {
                    "callback_data": (
                        update.callback_query.data[:100]
                        if update.callback_query.data
                        else None
                    ),
                }
            )

        logger.info(**log_data)

    except Exception as e:
        logger.error("log_update_details_error", error=str(e), exc_info=True)

    finally:
        # Store timing info in context for later use
        context.user_data["_update_start_time"] = start_time


async def log_handler_execution(handler_name: str, start_time: float = None) -> None:
    """Log handler execution time and details."""
    if start_time:
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        logger.info(
            "handler_executed", handler_name=handler_name, elapsed_ms=f"{elapsed:.2f}"
        )


def register_logging_middleware(app) -> None:
    """Register logging middleware for comprehensive backend visibility."""
    # This would be called in dispatcher to add pre-handler logging
    # The function above can be wrapped and added as a TypeHandler in group 0
    pass
