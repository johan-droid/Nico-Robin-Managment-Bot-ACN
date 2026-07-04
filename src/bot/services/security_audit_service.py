from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.models.audit import SecurityAudit
from src.bot.services.crypto_service import get_crypto_service


class SecurityAuditService:
    @staticmethod
    async def log_event(
        session: AsyncSession,
        event_type: str,
        severity: str,
        user_id: int | None = None,
        target_id: int | None = None,
        group_id: int | None = None,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str = "backend",
    ) -> SecurityAudit:
        # Validate severity level
        valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if severity not in valid_severities:
            severity = "MEDIUM"

        # Sanitize IP address
        sanitized_ip = None
        if ip_address:
            import ipaddress
            try:
                ipaddress.ip_address(ip_address)
                sanitized_ip = ip_address
            except ValueError:
                sanitized_ip = None

        crypto = get_crypto_service()

        # Create audit record with additional context
        record = SecurityAudit(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            target_id=target_id,
            group_id=group_id,
            reason=crypto.encrypt_text(reason),
            details=crypto.encrypt_mapping(details),
            ip_address=sanitized_ip,
            user_agent=user_agent,
            source=source,
            created_at=datetime.now(UTC),
        )

        # Rate limit audit logging to prevent DoS
        from src.bot.bot.middleware.rate_limiter import get_redis
        try:
            redis = get_redis()
            key = f"audit_rate_limit:{user_id or 'system'}"
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)  # 1 minute window
            elif count > 100:  # Rate limit
                await redis.expire(key, 3600)  # Extend to 1 hour if rate limited
                return record  # Return record but don't save to DB
        except Exception:
            pass  # If Redis fails, continue with DB logging

        session.add(record)
        await session.flush()

        # Log to security logger as well for real-time monitoring
        from src.bot.services.security_logger import SecurityLogger
        await SecurityLogger.log_event(
            f"audit_log_{event_type}",
            user_id=user_id,
            chat_id=group_id,
            details={
                "severity": severity,
                "target_id": target_id,
                "ip_address": sanitized_ip,
                "source": source
            }
        )

        return record

    @staticmethod
    async def get_recent_events(
        session: AsyncSession,
        limit: int = 50,
        severity: str | None = None,
        user_id: int | None = None
    ) -> list[SecurityAudit]:
        """Get recent security events with filtering"""
        from sqlalchemy import select, desc
        from src.bot.models.audit import SecurityAudit

        query = select(SecurityAudit).order_by(desc(SecurityAudit.created_at)).limit(limit)

        if severity:
            query = query.where(SecurityAudit.severity == severity)
        if user_id:
            query = query.where(SecurityAudit.user_id == user_id)

        result = await session.execute(query)
        return result.scalars().all()
