from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from telegram.ext import ContextTypes

from src.bot.config import settings
from src.bot.models.audit import ActionLog
from src.bot.models.group import Group
from src.bot.services.crypto_service import get_crypto_service
from src.bot.utils.formatters import format_action_log

logger = structlog.get_logger(__name__)


class AuditService:
    @staticmethod
    async def log_action(
        session: AsyncSession,
        group_id: int,
        action: str,
        actor_id: int | None = None,
        target_id: int | None = None,
        reason: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ActionLog:
        crypto = get_crypto_service()
        record = ActionLog(
            group_id=group_id,
            actor_id=actor_id,
            target_id=target_id,
            action=action,
            reason=crypto.encrypt_text(reason),
            extra=extra or {},
            created_at=datetime.now(UTC),
        )
        session.add(record)
        logger.info(
            "moderation_action",
            group_id=group_id,
            actor_id=actor_id,
            target_id=target_id,
            action=action,
            reason=reason,
            **(extra or {}),
        )
        await session.flush()
        return record

    @staticmethod
    async def forward_action(
        context: ContextTypes.DEFAULT_TYPE,
        group: Group,
        action: str,
        actor_label: str,
        target_label: str | None,
        reason: str | None,
    ) -> None:
        channel_id = group.log_channel_id or settings.log_channel_id
        if channel_id is None:
            return
        await context.bot.send_message(
            chat_id=channel_id,
            text=format_action_log(
                action=action,
                actor=actor_label,
                target=target_label or "N/A",
                group=group.title,
                reason=reason or "No reason provided",
            ),
        )
