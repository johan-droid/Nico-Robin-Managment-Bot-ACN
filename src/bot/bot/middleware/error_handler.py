"""Global error handler — prevents stack trace leakage.

Catches ALL unhandled exceptions, sends safe messages to users,
and forwards full diagnostics to the log channel.
"""

from __future__ import annotations

import html
import time
import traceback

import structlog
from telegram import Update
from telegram.error import (
    BadRequest,
    ChatMigrated,
    Forbidden,
    InvalidToken,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)
from telegram.ext import ContextTypes

from src.bot.config import settings

logger = structlog.get_logger(__name__)
_err_times: list[float] = []


async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    err = ctx.error
    if err is None or type(err).__name__ == "_StopProcessing":
        return
    cat, user_msg, sev = _classify(err)
    info = _info(update)
    tb = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    logger.error(
        "unhandled_exception", category=cat, error=str(err)[:500], severity=sev, **info
    )
    logger.error("unhandled_exception_traceback", traceback=tb, **info)
    if isinstance(update, Update) and update.effective_message and user_msg:
        try:
            await update.effective_message.reply_text(user_msg)
        except Exception:
            pass
    await _report(ctx, err, cat, sev, info)


def _classify(e):
    if isinstance(e, InvalidToken):
        return ("auth", "🛡️ Auth error. Contact admin.", "CRITICAL")
    if isinstance(e, Forbidden):
        return ("permission", "🌸 I lack permission for that.", "LOW")
    if isinstance(e, BadRequest):
        m = str(e).lower()
        for p in ("not modified", "not found", "too old"):
            if p in m:
                return ("benign", "", "IGNORE")
        return ("bad_request", "🌸 Bad request format.", "LOW")
    if isinstance(e, RetryAfter):
        return ("rate_limit", f"🛡️ Rate limited. Retry in {e.retry_after}s.", "MEDIUM")
    if isinstance(e, TimedOut | NetworkError):
        return ("network", "🌸 Network issue. Try again.", "MEDIUM")
    if isinstance(e, ChatMigrated):
        return ("migration", "🌸 Chat migrated.", "LOW")
    if isinstance(e, TelegramError):
        return ("telegram_api", "🌸 Telegram issue. Try again.", "MEDIUM")
    t = f"{type(e).__module__}.{type(e).__name__}".lower()
    if "sqlalchemy" in t or "asyncpg" in t:
        return ("database", "🌸 Temp data issue. Try again.", "HIGH")
    return ("unknown", "🌸 Unexpected error. Team notified.", "HIGH")


def _info(update):
    d = {}
    if isinstance(update, Update):
        if update.effective_user:
            d["user_id"] = update.effective_user.id
        if update.effective_chat:
            d["chat_id"] = update.effective_chat.id
        if update.effective_message and update.effective_message.text:
            t = update.effective_message.text
            if t.startswith("/"):
                d["command"] = t.split()[0][:50]
    return d


async def _report(ctx, err, cat, sev, info):
    if sev == "IGNORE" or not settings.log_channel_id:
        return
    now = time.time()
    _err_times[:] = [t for t in _err_times if t > now - 60]
    if len(_err_times) >= 10:
        return
    _err_times.append(now)
    tb = "".join(traceback.format_exception(type(err), err, err.__traceback__))[-1500:]
    emj = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}.get(sev, "⚪")
    cat_esc = html.escape(str(cat))
    err_name_esc = html.escape(type(err).__name__)
    err_msg_esc = html.escape(str(err)[:300])

    r = (
        f"{emj} <b>Error [{sev}]</b>\n"
        f"📋 {cat_esc}\n"
        f"❌ <code>{err_name_esc}</code>\n"
        f"📝 {err_msg_esc}\n"
    )
    if info.get("user_id"):
        r += f"👤 <code>{info['user_id']}</code>\n"
    if info.get("chat_id"):
        r += f"💬 <code>{info['chat_id']}</code>\n"
    if info.get("command"):
        r += f"🔧 <code>{html.escape(str(info['command']))}</code>\n"

    # Escape traceback and wrap in pre
    tb_esc = html.escape(tb)
    r += f"\n<pre>{tb_esc}</pre>"

    try:
        await ctx.bot.send_message(
            chat_id=settings.log_channel_id, text=r[:4096], parse_mode="HTML"
        )
    except Exception:
        logger.error("report_failed", err=str(err)[:200])


async def global_error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Backward-compatible alias for error_handler."""

    await error_handler(update, ctx)
