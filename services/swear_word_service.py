from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.swear_word import SwearViolation, SwearWord

SeverityLevel = Literal["mild", "moderate", "severe"]
PunishmentType = Literal["mute", "temp_ban", "perm_ban"]


@dataclass(frozen=True)
class SwearWordMatch:
    swear_word: SwearWord
    matched_text: str
    severity: SeverityLevel
    punishment_type: PunishmentType
    duration: int


@dataclass(frozen=True)
class PunishmentResult:
    action: str
    duration: int
    reason: str
    escalate: bool = False


class SwearWordService:
    VALID_SEVERITIES = {"mild", "moderate", "severe"}
    VALID_PUNISHMENTS = {"mute", "temp_ban", "perm_ban"}

    @staticmethod
    async def add_swear_word(
        session: AsyncSession,
        group_id: int,
        word: str,
        severity: SeverityLevel = "moderate",
        punishment_type: PunishmentType = "mute",
        duration: int = 300,
        is_regex: bool = False,
        created_by: int | None = None,
    ) -> SwearWord:
        if severity not in SwearWordService.VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {severity}")
        if punishment_type not in SwearWordService.VALID_PUNISHMENTS:
            raise ValueError(f"Invalid punishment type: {punishment_type}")
        if duration < 0:
            raise ValueError("Duration must be non-negative")

        normalized = word.lower().strip()
        result = await session.execute(
            select(SwearWord).where(
                SwearWord.group_id == group_id,
                SwearWord.word == normalized,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            swear_word = SwearWord(
                group_id=group_id,
                word=normalized,
                severity=severity,
                punishment_type=punishment_type,
                duration=duration,
                is_regex=is_regex,
                created_by=created_by,
            )
            session.add(swear_word)
        else:
            existing.severity = severity
            existing.punishment_type = punishment_type
            existing.duration = duration
            existing.is_regex = is_regex
            existing.created_by = created_by
            swear_word = existing

        await session.flush()
        return swear_word

    @staticmethod
    async def remove_swear_word(session: AsyncSession, group_id: int, word: str) -> int:
        result = await session.execute(
            delete(SwearWord).where(
                SwearWord.group_id == group_id,
                SwearWord.word == word.lower().strip(),
            )
        )
        return int(result.rowcount or 0)

    @staticmethod
    async def list_swear_words(session: AsyncSession, group_id: int) -> list[SwearWord]:
        result = await session.execute(
            select(SwearWord)
            .where(SwearWord.group_id == group_id)
            .order_by(SwearWord.word)
        )
        return list(result.scalars().all())

    @staticmethod
    async def match_swear_words(
        session: AsyncSession,
        group_id: int,
        text: str,
    ) -> list[SwearWordMatch]:
        if not text.strip():
            return []

        swear_words = await SwearWordService.list_swear_words(session, group_id)
        text_lower = text.lower()
        matches: list[SwearWordMatch] = []

        for swear_word in swear_words:
            if swear_word.is_regex:
                try:
                    match = re.search(swear_word.word, text, flags=re.IGNORECASE)
                    if match:
                        matches.append(
                            SwearWordMatch(
                                swear_word=swear_word,
                                matched_text=match.group(0),
                                severity=swear_word.severity,
                                punishment_type=swear_word.punishment_type,
                                duration=swear_word.duration,
                            )
                        )
                except re.error:
                    continue  # Skip invalid regex patterns
            else:
                # Word boundary matching for non-regex patterns
                pattern = r"\b" + re.escape(swear_word.word) + r"\b"
                if re.search(pattern, text_lower):
                    matches.append(
                        SwearWordMatch(
                            swear_word=swear_word,
                            matched_text=swear_word.word,
                            severity=swear_word.severity,
                            punishment_type=swear_word.punishment_type,
                            duration=swear_word.duration,
                        )
                    )

        return matches

    @staticmethod
    async def calculate_punishment(
        session: AsyncSession,
        group_id: int,
        user_id: int,
        match: SwearWordMatch,
    ) -> PunishmentResult:
        """Calculate punishment based on severity and user history"""

        # Get user's violation history
        result = await session.execute(
            select(SwearViolation).where(
                SwearViolation.group_id == group_id,
                SwearViolation.user_id == user_id,
            )
        )
        violations = list(result.scalars().all())

        # Count violations in last 24 hours
        current_time = int(time.time())
        recent_violations = [
            v
            for v in violations
            if current_time - v.created_at <= 86400  # 24 hours
        ]

        violation_count = len(recent_violations)

        # Base punishment from the word itself
        base_action = match.punishment_type
        base_duration = match.duration

        # Escalate based on violation count
        if violation_count >= 3:  # 3+ violations in 24h
            if match.severity == "mild":
                action = "temp_ban"
                duration = 3600  # 1 hour
            elif match.severity == "moderate":
                action = "temp_ban"
                duration = 86400  # 24 hours
            else:  # severe
                action = "perm_ban"
                duration = 0
            escalate = True
        elif violation_count >= 1:  # Repeat offender
            if match.severity == "mild":
                action = "mute"
                duration = max(base_duration * 2, 600)  # At least 10 minutes
            elif match.severity == "moderate":
                action = "temp_ban"
                duration = 3600  # 1 hour
            else:  # severe
                action = "temp_ban"
                duration = 86400  # 24 hours
            escalate = True
        else:  # First offense
            action = base_action
            duration = base_duration
            escalate = False

        return PunishmentResult(
            action=action,
            duration=duration,
            reason=f"Swear word detected: {match.matched_text} ({match.severity})",
            escalate=escalate,
        )

    @staticmethod
    async def record_violation(
        session: AsyncSession,
        group_id: int,
        user_id: int,
        match: SwearWordMatch,
        punishment: PunishmentResult,
    ) -> SwearViolation:
        violation = SwearViolation(
            group_id=group_id,
            user_id=user_id,
            swear_word=match.matched_text,
            severity=match.severity,
            punishment_given=f"{punishment.action}:{punishment.duration}",
            created_at=int(time.time()),
        )
        session.add(violation)
        await session.flush()
        return violation

    @staticmethod
    async def get_violation_count(
        session: AsyncSession,
        group_id: int,
        user_id: int,
        hours: int = 24,
    ) -> int:
        """Get violation count for user in specified hours"""
        cutoff_time = int(time.time()) - (hours * 3600)
        result = await session.execute(
            select(SwearViolation).where(
                SwearViolation.group_id == group_id,
                SwearViolation.user_id == user_id,
                SwearViolation.created_at >= cutoff_time,
            )
        )
        return len(list(result.scalars().all()))
