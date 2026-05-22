"""Security audit logger — tracks and alerts on all security events.

Logs to both database and log channel for forensic analysis.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from src.bot.bot.middleware.rate_limiter import get_redis
from src.bot.config import settings
from src.bot.database import async_session_factory
from src.bot.services.security_audit_service import SecurityAuditService

logger = structlog.get_logger(__name__)
_ALERT_KEY = "sec:alert_times"


class SecurityLogger:
    """Centralized security event tracking."""

    @staticmethod
    async def log_event(
        event_type: str,
        user_id: int | None = None,
        chat_id: int | None = None,
        details: dict[str, Any] | None = None,
        severity: str = "MEDIUM",
    ) -> None:
        """Log a security event to Redis stream and structured logs."""
        event = {
            "type": event_type,
            "user_id": str(user_id) if user_id else "",
            "chat_id": str(chat_id) if chat_id else "",
            "severity": severity,
            "timestamp": str(time.time()),
            "details": str(details or {}),
        }

        # Structured log
        logger.warning("security_event", **event)

        # Store in Redis stream (last 1000 events, auto-trimmed)
        try:
            redis = get_redis()
            await redis.xadd("security:events", event, maxlen=1000)
        except Exception:
            pass
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    await SecurityAuditService.log_event(
                        session=session,
                        event_type=event_type,
                        severity=severity,
                        user_id=user_id,
                        group_id=chat_id,
                        reason=event_type,
                        details=details or {},
                    )
        except Exception:
            pass

    @staticmethod
    async def alert_to_channel(
        bot: Any,
        event_type: str,
        details: str,
        severity: str = "HIGH",
    ) -> None:
        """Send real-time security alert to log channel (rate-limited)."""
        if not settings.log_channel_id:
            return

        # Rate limit: max 5 alerts per minute
        try:
            redis = get_redis()
            now = time.time()
            await redis.zremrangebyscore(_ALERT_KEY, 0, now - 60)
            count = await redis.zcard(_ALERT_KEY)
            if count >= 5:
                return
            await redis.zadd(_ALERT_KEY, {f"{now}": now})
            await redis.expire(_ALERT_KEY, 120)
        except Exception:
            pass

        emj = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(severity, "⚪")
        msg = (
            f"{emj} **Security Alert [{severity}]**\n\n"
            f"🛡️ **Event:** {event_type}\n"
            f"📝 **Details:** {details[:500]}\n"
            f"🕐 **Time:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        )
        try:
            await bot.send_message(
                chat_id=settings.log_channel_id,
                text=msg,
                parse_mode="Markdown",
            )
        except Exception:
            logger.error("security_alert_failed", event=event_type)

    @staticmethod
    async def get_recent_events(count: int = 50) -> list[dict]:
        """Retrieve recent security events from Redis stream."""
        try:
            redis = get_redis()
            events = await redis.xrevrange("security:events", count=count)
            return [
                {"id": eid, **{k: v for k, v in data.items()}} for eid, data in events
            ]
        except Exception:
            return []
