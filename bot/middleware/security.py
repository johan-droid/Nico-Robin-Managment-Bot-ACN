"""Security middleware — rate limiting, anti-spam, and abuse detection.

This module provides the core security layer that protects the bot from:
- Command flooding (per-user, per-group, global)
- Automated abuse (repeated violations → auto-cooldown)
- Resource exhaustion attacks
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from bot.middleware.rate_limiter import get_redis
from config import settings

logger = structlog.get_logger(__name__)

# Redis key prefixes
_USER_RATE_KEY = "rl:user:{user_id}"
_GROUP_RATE_KEY = "rl:group:{chat_id}"
_GLOBAL_RATE_KEY = "rl:global"
_COOLDOWN_KEY = "rl:cd:{user_id}"
_VIOLATION_KEY = "rl:viol:{user_id}"
_WINDOW = 60  # 1-minute sliding window


async def rate_limit_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check rate limits. Returns True if the update should be BLOCKED.

    Three-tier rate limiting:
    1. Per-user: prevents individual spam
    2. Per-group: prevents coordinated group spam
    3. Global: prevents total bot resource exhaustion
    """
    user = update.effective_user
    chat = update.effective_chat

    # Only rate-limit command messages (not passive events like joins)
    message = update.effective_message
    if not message or not message.text or not message.text.startswith("/"):
        return False

    if user is None:
        return False

    # Captain and sudo users bypass rate limits
    if (
        user.id == settings.captain_id
        or user.id in settings.commander_ids
        or user.id in settings.sudo_users
    ):
        return False

    redis = get_redis()
    now = time.time()
    blocked = False
    violation_source = ""

    try:
        # ── Check cooldown first ──
        cooldown_key = _COOLDOWN_KEY.format(user_id=user.id)
        if await redis.exists(cooldown_key):
            ttl = await redis.ttl(cooldown_key)
            if message:
                try:
                    await message.reply_text(
                        f"🛡️ You're on cooldown. Try again in {ttl}s."
                    )
                except Exception:
                    pass
            return True

        # ── Per-user rate limit ──
        user_key = _USER_RATE_KEY.format(user_id=user.id)
        user_count = await _increment_sliding_window(redis, user_key, now)
        if user_count > settings.rate_limit_user:
            blocked = True
            violation_source = "user"

        # ── Per-group rate limit ──
        if not blocked and chat:
            group_key = _GROUP_RATE_KEY.format(chat_id=chat.id)
            group_count = await _increment_sliding_window(redis, group_key, now)
            if group_count > settings.rate_limit_group:
                blocked = True
                violation_source = "group"

        # ── Global rate limit ──
        if not blocked:
            global_count = await _increment_sliding_window(redis, _GLOBAL_RATE_KEY, now)
            if global_count > settings.rate_limit_global:
                blocked = True
                violation_source = "global"

        # ── Handle violation ──
        if blocked:
            await _handle_violation(redis, user, chat, violation_source, message)
    except Exception as e:
        logger.error("rate_limit_redis_error", error=str(e))
        return False

    return blocked


async def _increment_sliding_window(redis: Any, key: str, now: float) -> int:
    """Increment a Redis sorted-set sliding window counter."""
    member = f"{now}:{id(now)}"
    pipe = redis.pipeline()
    pipe.zadd(key, {member: now})
    pipe.zremrangebyscore(key, 0, now - _WINDOW)
    pipe.zcard(key)
    pipe.expire(key, _WINDOW * 2)
    _, _, count, _ = await pipe.execute()
    return int(count)


async def _handle_violation(
    redis: Any, user: Any, chat: Any, source: str, message: Any
) -> None:
    """Handle a rate limit violation — escalate if repeated."""
    # Track violations
    viol_key = _VIOLATION_KEY.format(user_id=user.id)
    violation_count = await redis.incr(viol_key)
    await redis.expire(viol_key, 300)  # Track over 5 minutes

    # Escalate: apply cooldown
    cooldown_seconds = settings.rate_limit_cooldown
    if violation_count >= settings.rate_limit_ban_threshold:
        cooldown_seconds = cooldown_seconds * 5  # 2.5 min cooldown for repeat offenders

    cooldown_key = _COOLDOWN_KEY.format(user_id=user.id)
    await redis.set(cooldown_key, "1", ex=cooldown_seconds)

    logger.warning(
        "rate_limit_violation",
        user_id=user.id,
        username=user.username,
        chat_id=chat.id if chat else None,
        source=source,
        violation_count=int(violation_count),
        cooldown_seconds=cooldown_seconds,
    )

    # Notify user
    if message:
        try:
            if violation_count >= settings.rate_limit_ban_threshold:
                await message.reply_text(
                    f"🛡️ **Rate limit exceeded (repeated offense).**\n"
                    f"You are on a {cooldown_seconds}s cooldown.\n"
                    f"⚠️ Continued abuse may result in a permanent ban.",
                )
            else:
                await message.reply_text(
                    f"🛡️ Slow down! Rate limit reached.\nCooldown: {cooldown_seconds}s.",
                )
        except Exception:
            pass

    # Log security event
    try:
        from services.security_logger import SecurityLogger

        await SecurityLogger.log_event(
            event_type="rate_limit_violation",
            user_id=user.id,
            chat_id=chat.id if chat else None,
            details={
                "source": source,
                "violation_count": int(violation_count),
                "cooldown_seconds": cooldown_seconds,
            },
        )
    except Exception:
        pass
