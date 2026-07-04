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
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str = "backend",
    ) -> None:
        """Log a security event to Redis stream and structured logs."""
        # Validate and sanitize inputs
        sanitized_details = {}
        if details:
            for key, value in details.items():
                if key.lower() in ["password", "token", "secret", "key"]:
                    sanitized_details[key] = "[REDACTED]"
                else:
                    sanitized_details[key] = str(value)[:500]  # Limit size

        event = {
            "type": event_type,
            "user_id": str(user_id) if user_id else "",
            "chat_id": str(chat_id) if chat_id else "",
            "severity": severity.upper(),
            "timestamp": str(time.time()),
            "details": str(sanitized_details),
            "ip_address": ip_address or "",
            "user_agent": user_agent or "",
            "source": source,
        }

        # Validate severity
        if event["severity"] not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            event["severity"] = "MEDIUM"

        # Structured log with severity-based logging
        log_method = {
            "CRITICAL": logger.critical,
            "HIGH": logger.error,
            "MEDIUM": logger.warning,
            "LOW": logger.info
        }.get(event["severity"], logger.warning)

        log_method("security_event", **event)

        # Store in Redis stream with enhanced security
        try:
            redis = get_redis()
            # Use a pipeline for atomic operations
            async with redis.pipeline() as pipe:
                # Add to main stream (last 1000 events)
                await pipe.xadd("security:events", event, maxlen=1000)

                # Add to severity-specific streams for filtering
                await pipe.xadd(f"security:events:{event['severity']}", event, maxlen=500)

                # Add to user-specific stream if user_id exists
                if user_id:
                    await pipe.xadd(f"security:user:{user_id}", event, maxlen=200)

                await pipe.execute()
        except Exception as e:
            logger.error("redis_security_log_failed", error=str(e))

        # Database audit logging with rate limiting
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    await SecurityAuditService.log_event(
                        session=session,
                        event_type=event_type,
                        severity=event["severity"],
                        user_id=user_id,
                        group_id=chat_id,
                        reason=event_type,
                        details=sanitized_details,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        source=source,
                    )
        except Exception as e:
            logger.error("db_audit_log_failed", error=str(e))

        # Alert for critical events
        if event["severity"] in ["CRITICAL", "HIGH"]:
            try:
                from src.bot.bot.instance import get_bot
                bot = get_bot()
                if bot:
                    await SecurityLogger.alert_to_channel(
                        bot,
                        event_type,
                        f"User {user_id} in chat {chat_id}: {str(sanitized_details)[:200]}",
                        severity=event["severity"]
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
