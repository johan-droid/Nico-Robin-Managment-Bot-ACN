"""Global error handler — prevents stack trace leakage.

Catches ALL unhandled exceptions, sends safe messages to users,
and forwards full diagnostics to the log channel.
"""

from __future__ import annotations

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

from config import settings

logger = structlog.get_logger(__name__)
_err_times: list[float] = []


async def global_error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    err = ctx.error
    if err is None or type(err).__name__ == "_StopProcessing":
        return
    cat, user_msg, sev = _classify(err)
    info = _info(update)
    logger.error(
        "unhandled_exception", category=cat, error=str(err)[:500], severity=sev, **info
    )
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
    if isinstance(e, (TimedOut, NetworkError)):
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
    r = (
        f"{emj} **Error [{sev}]**\n📋 {cat}\n❌ `{type(err).__name__}`\n"
        f"📝 {str(err)[:300]}\n"
    )
    if info.get("user_id"):
        r += f"👤 `{info['user_id']}`\n"
    if info.get("chat_id"):
        r += f"💬 `{info['chat_id']}`\n"
    if info.get("command"):
        r += f"🔧 `{info['command']}`\n"
    r += f"\n```\n{tb}\n```"
    try:
        await ctx.bot.send_message(
            chat_id=settings.log_channel_id, text=r[:4000], parse_mode="Markdown"
        )
    except Exception:
        logger.error("report_failed", err=str(err)[:200])
