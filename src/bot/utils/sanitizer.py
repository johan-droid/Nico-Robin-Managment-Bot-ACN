"""Input sanitization — defense-in-depth protection against injection attacks.

Protects against:
- SQL injection via command arguments
- Telegram Markdown/HTML injection
- Path traversal attacks
- Oversized input payloads
- Script/code injection
"""

from __future__ import annotations

import html
import re
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import cast

from telegram import Update
from telegram.ext import ContextTypes

# ── Constants ──
MAX_ARG_LENGTH = 500
MAX_TOTAL_LENGTH = 2000
MAX_ARGS_COUNT = 20

# SQL injection patterns (case-insensitive)
_SQL_PATTERNS = re.compile(
    r"(?:--|;|/\*|\*/|"
    r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|UNION|"
    r"TRUNCATE|GRANT|REVOKE|INTO|FROM|WHERE|HAVING|ORDER\s+BY|"
    r"GROUP\s+BY|OR\s+1\s*=\s*1|AND\s+1\s*=\s*1|"
    r"xp_|sp_|0x[0-9a-fA-F]+)\b)",
    re.IGNORECASE,
)

# Script injection patterns
_SCRIPT_PATTERNS = re.compile(
    r"<\s*script|javascript:|on\w+\s*=|<\s*iframe|<\s*object|<\s*embed|"
    r"<\s*form|<\s*input|data:text/html|vbscript:",
    re.IGNORECASE,
)

# Path traversal patterns
_PATH_TRAVERSAL = re.compile(r"\.\./|\.\.\\|%2e%2e|%252e%252e", re.IGNORECASE)

# Telegram Markdown special characters that can be used for formatting injection
_MARKDOWN_INJECT = re.compile(r"[\[\]`]")


def sanitize_text(text: str, *, allow_markdown: bool = False) -> str:
    """Sanitize a text string for safe storage and display.

    Args:
        text: Raw input text.
        allow_markdown: If True, preserves basic Markdown (* and _).
    """
    if not text:
        return text

    # Length enforcement
    text = text[:MAX_TOTAL_LENGTH]

    # Strip null bytes
    text = text.replace("\x00", "")

    # HTML entity encoding
    text = html.escape(text, quote=True)

    # Block script injection
    text = _SCRIPT_PATTERNS.sub("[blocked]", text)

    # Block path traversal
    text = _PATH_TRAVERSAL.sub("", text)

    if not allow_markdown:
        # Escape Markdown injection characters
        text = _MARKDOWN_INJECT.sub("", text)

    return text.strip()


def sanitize_args(args: list[str] | None) -> list[str]:
    """Sanitize a list of command arguments.

    - Limits count to MAX_ARGS_COUNT
    - Limits each arg to MAX_ARG_LENGTH
    - Strips dangerous patterns
    """
    if not args:
        return []

    clean: list[str] = []
    for arg in args[:MAX_ARGS_COUNT]:
        arg = arg[:MAX_ARG_LENGTH]
        arg = arg.replace("\x00", "")
        arg = _SCRIPT_PATTERNS.sub("", arg)
        arg = _PATH_TRAVERSAL.sub("", arg)
        arg = arg.strip()
        if arg:
            clean.append(arg)
    return clean


def contains_sql_injection(text: str) -> bool:
    """Check if text contains SQL injection patterns.

    Note: This is a secondary defense. Primary protection comes from
    SQLAlchemy's parameterized queries. This catches deliberate attempts.
    """
    if not text:
        return False
    return bool(_SQL_PATTERNS.search(text))


def contains_dangerous_input(text: str) -> bool:
    """Check if text matches SQL, script, or path traversal attack patterns."""
    if not text:
        return False
    return bool(
        _SQL_PATTERNS.search(text)
        or _SCRIPT_PATTERNS.search(text)
        or _PATH_TRAVERSAL.search(text)
    )


def validate_numeric_arg(
    value: str, *, min_val: int | None = None, max_val: int | None = None
) -> int | None:
    """Safely parse and validate a numeric argument.

    Returns None if the value is invalid, instead of raising an exception.
    """
    try:
        num = int(value.strip())
    except (ValueError, TypeError):
        return None

    if min_val is not None and num < min_val:
        return None
    if max_val is not None and num > max_val:
        return None
    return num


def validate_telegram_id(value: str) -> int | None:
    """Validate a Telegram user/chat ID.

    Telegram IDs are signed 64-bit integers.
    """
    num = validate_numeric_arg(value, min_val=-(2**63), max_val=2**63 - 1)
    return num


# ── Decorator ──

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


def sanitize_input(func: Handler) -> Handler:
    """Decorator that automatically sanitizes context.args before handler runs.

    Usage:
        @sanitize_input
        async def my_command(update, context):
            # context.args is already cleaned
            ...
    """

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Sanitize command arguments
        if context.args:
            original_args = list(context.args)
            clean = sanitize_args(original_args)

            # Check for SQL injection in the combined input
            combined = " ".join(original_args)
            if contains_sql_injection(combined):
                import structlog

                logger = structlog.get_logger(__name__)
                user = update.effective_user
                logger.warning(
                    "sql_injection_attempt",
                    user_id=user.id if user else None,
                    input=combined[:200],
                )
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "🛡️ Suspicious input detected and blocked."
                    )
                # Log security event
                try:
                    from src.bot.services.security_logger import SecurityLogger

                    await SecurityLogger.log_event(
                        event_type="sql_injection_attempt",
                        user_id=user.id if user else None,
                        chat_id=(
                            update.effective_chat.id if update.effective_chat else None
                        ),
                        details={"input": combined[:500]},
                    )
                except Exception:
                    pass
                return

            # Replace args with sanitized version
            # context.args is a tuple, we need to use _args
            context._args = clean  # noqa: SLF001

        await func(update, context)

    return cast(Handler, wrapper)
