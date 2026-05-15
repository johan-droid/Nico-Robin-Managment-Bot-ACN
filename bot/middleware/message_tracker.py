"""Message tracker middleware — passively counts messages for profile stats.

Runs on every message at handler group=1 (after plugins). Uses Redis
buffering to batch DB writes for performance.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from bot.middleware.rate_limiter import get_redis

logger = structlog.get_logger(__name__)

# Redis keys
_MSG_COUNT_KEY = "mt:{user_id}:{group_id}:msgs"
_MSG_TYPE_KEY = "mt:{user_id}:{group_id}:type:{type}"
_HOUR_KEY = "mt:{user_id}:{group_id}:hour:{hour}"
_DAY_KEY = "mt:{user_id}:{group_id}:days"
_FLUSH_THRESHOLD = 25  # Flush to DB every N messages per user-group


async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Track message statistics passively. Non-blocking, never raises."""
    try:
        msg = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        if not msg or not user or not chat:
            return
        if user.is_bot:
            return
        if chat.type not in ("group", "supergroup"):
            return

        redis = get_redis()
        uid = user.id
        gid = chat.id
        now = datetime.now(UTC)
        hour = now.hour

        pipe = redis.pipeline()

        # Increment total message count
        count_key = _MSG_COUNT_KEY.format(user_id=uid, group_id=gid)
        pipe.incr(count_key)
        pipe.expire(count_key, 7200)  # 2h TTL — flushed well before

        # Track message type
        msg_type = _detect_type(msg)
        if msg_type:
            type_key = _MSG_TYPE_KEY.format(user_id=uid, group_id=gid, type=msg_type)
            pipe.incr(type_key)
            pipe.expire(type_key, 7200)

        # Track hourly activity
        hour_key = _HOUR_KEY.format(user_id=uid, group_id=gid, hour=hour)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 7200)

        # Track unique active days
        day_str = now.strftime("%Y-%m-%d")
        day_key = _DAY_KEY.format(user_id=uid, group_id=gid)
        pipe.sadd(day_key, day_str)
        pipe.expire(day_key, 7200)

        results = await pipe.execute()
        current_count = int(results[0])

        # Flush to DB periodically
        if current_count >= _FLUSH_THRESHOLD:
            context.application.create_task(_flush_to_db(redis, uid, gid))

    except Exception:
        pass  # Never block message processing


def _detect_type(msg) -> str | None:
    """Detect message content type."""
    if msg.sticker:
        return "sticker"
    if msg.photo:
        return "photo"
    if msg.video or msg.video_note:
        return "video"
    if msg.voice or msg.audio:
        return "voice"
    if msg.document:
        return "document"
    if msg.text and msg.text.startswith("/"):
        return "command"
    return None


async def _flush_to_db(redis, user_id: int, group_id: int) -> None:
    """Flush accumulated Redis counters to the database."""
    from database import async_session_factory
    from services.profile_service import ProfileService

    try:
        # Gather all counters
        count_key = _MSG_COUNT_KEY.format(user_id=user_id, group_id=group_id)
        msgs = int(await redis.getdel(count_key) or 0)

        type_counts = {}
        for t in ("sticker", "photo", "video", "voice", "document", "command"):
            tk = _MSG_TYPE_KEY.format(user_id=user_id, group_id=group_id, type=t)
            val = await redis.getdel(tk) or 0
            type_counts[t] = int(val)

        # Hourly activity
        hourly = {}
        for h in range(24):
            hk = _HOUR_KEY.format(user_id=user_id, group_id=group_id, hour=h)
            val = await redis.getdel(hk) or 0
            if int(val) > 0:
                hourly[str(h)] = int(val)

        # Active days
        day_key = _DAY_KEY.format(user_id=user_id, group_id=group_id)
        day_members = await redis.smembers(day_key)
        new_days = len(day_members) if day_members else 0
        await redis.delete(day_key)

        # Write to DB
        async with async_session_factory() as session:
            async with session.begin():
                await ProfileService.increment_stats(
                    session,
                    user_id,
                    group_id,
                    messages=msgs,
                    stickers=type_counts.get("sticker", 0),
                    photos=type_counts.get("photo", 0),
                    videos=type_counts.get("video", 0),
                    voice=type_counts.get("voice", 0),
                    documents=type_counts.get("document", 0),
                    commands=type_counts.get("command", 0),
                    hourly=hourly,
                    new_days=new_days,
                )

    except Exception as e:
        logger.error("message_tracker_flush_error", error=str(e)[:200])
