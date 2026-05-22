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
    ) -> SecurityAudit:
        crypto = get_crypto_service()
        record = SecurityAudit(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            target_id=target_id,
            group_id=group_id,
            reason=crypto.encrypt_text(reason),
            details=crypto.encrypt_mapping(details),
            ip_address=ip_address,
            created_at=datetime.now(UTC),
        )
        session.add(record)
        await session.flush()
        return record
