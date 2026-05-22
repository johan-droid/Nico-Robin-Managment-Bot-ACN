from __future__ import annotations

import re
from collections.abc import Mapping
from functools import lru_cache
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from src.bot.config import Settings, settings

try:
    from profanity_check import predict_prob

    PROFANITY_CHECK_AVAILABLE = True
except ImportError:
    predict_prob = None
    PROFANITY_CHECK_AVAILABLE = False

try:
    from src.bot.database import async_session_factory
    from src.bot.services.swear_word_service import SwearWordService

    SWEAR_WORD_SERVICE_AVAILABLE = True
except ImportError:
    SWEAR_WORD_SERVICE_AVAILABLE = False

ModerationAction = Literal[
    "none",
    "warn",
    "delete",
    "ban",
    "notify_admin",
    "delete_warn",
]


class ModerationResult(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    category: str = "safe"
    action: ModerationAction = "none"
    rationale: str | None = None

    @classmethod
    def safe(cls) -> ModerationResult:
        return cls(score=0.0, category="safe", action="none")


class Moderator(Protocol):
    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        """Return a moderation decision for a message."""


class DisabledModerator:
    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        del message_text, context
        return ModerationResult.safe()


class TraditionalMLModerator:
    def __init__(self) -> None:
        self.doxxing_patterns = [
            re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", re.IGNORECASE),
            re.compile(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b\d+\s+[A-Za-z]+\s+"
                r"(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|"
                r"Court|Ct|Way|Place|Pl)\b",
                re.IGNORECASE,
            ),
        ]
        self.spam_patterns = [
            re.compile(r"https?://[^\s]+", re.IGNORECASE),
            re.compile(r"www\.[^\s]+", re.IGNORECASE),
            re.compile(
                r"\b(buy|sell|discount|offer|deal|free|win|prize|click|visit|"
                r"check out|limited time)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b\$\d+\.?\d*\b", re.IGNORECASE),
        ]
        self.self_harm_patterns = [
            re.compile(
                r"\b(kill|die|suicide|end my life|hurt myself|self.harm|cutting|"
                r"overdose)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(want to die|don.t want to live|better off dead)\b",
                re.IGNORECASE,
            ),
        ]
        self.safe_indicators = {
            "hello",
            "hi",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "good",
            "great",
            "nice",
        }
        self.max_content_length = 10000

    def _detect_pattern(self, text: str, patterns: list[re.Pattern[str]]) -> bool:
        return any(pattern.search(text) for pattern in patterns)

    async def _detect_swear_words(
        self,
        message_text: str,
        group_id: int | None,
    ) -> tuple[float, str | None]:
        if not SWEAR_WORD_SERVICE_AVAILABLE or group_id is None:
            return 0.0, None
        try:
            async with async_session_factory() as session:
                matches = await SwearWordService.match_swear_words(
                    session,
                    group_id,
                    message_text,
                )
        except Exception:
            return 0.0, None

        if not matches:
            return 0.0, None
        highest_match = max(
            matches,
            key=lambda match: (
                0
                if match.severity == "mild"
                else 1 if match.severity == "moderate" else 2
            ),
        )
        score = 0.9 if highest_match.severity == "severe" else 0.7
        return score, f"swear_word_{highest_match.severity}"

    @staticmethod
    def _toxicity_action(probability: float) -> tuple[str, ModerationAction]:
        if probability < 0.45:
            return "safe", "none"
        if probability < 0.70:
            return "harassment", "warn"
        if probability < 0.95:
            return "toxicity", "delete_warn"
        return "hate_speech", "ban"

    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        if len(message_text) > self.max_content_length:
            return ModerationResult.safe()

        text_lower = message_text.lower().strip()
        if text_lower in self.safe_indicators or text_lower.startswith(
            tuple(self.safe_indicators)
        ):
            return ModerationResult.safe()

        if self._detect_pattern(message_text, self.self_harm_patterns):
            return ModerationResult(
                score=0.99,
                category="self_harm",
                action="notify_admin",
                rationale="Self-harm content detected",
            )
        if self._detect_pattern(message_text, self.doxxing_patterns):
            return ModerationResult(
                score=0.90,
                category="doxxing",
                action="delete_warn",
                rationale="Personal information detected",
            )

        spam_matches = sum(
            1 for pattern in self.spam_patterns if pattern.search(message_text)
        )
        if spam_matches >= 2:
            return ModerationResult(
                score=0.80,
                category="spam_promo",
                action="delete",
                rationale="Spam or promotional content detected",
            )

        swear_score, swear_category = await self._detect_swear_words(
            message_text,
            (
                context.get("group_id")
                if isinstance(context.get("group_id"), int)
                else None
            ),
        )
        if swear_score >= 0.7:
            action: ModerationAction = (
                "delete_warn"
                if swear_category is not None and "severe" in swear_category
                else "warn"
            )
            return ModerationResult(
                score=swear_score,
                category=swear_category or "swear_word_moderate",
                action=action,
                rationale="Swear word detected",
            )

        probability = 0.0
        if PROFANITY_CHECK_AVAILABLE and predict_prob is not None:
            try:
                probability = float(predict_prob([message_text])[0])
            except Exception:
                probability = 0.0

        category, action = self._toxicity_action(probability)
        if action == "none":
            return ModerationResult.safe()
        rationale = (
            "Traditional ML offline moderation"
            if PROFANITY_CHECK_AVAILABLE
            else "Traditional moderation fallback"
        )
        return ModerationResult(
            score=probability,
            category=category,
            action=action,
            rationale=rationale,
        )


class ModerationEngine:
    def __init__(self, provider: Moderator) -> None:
        self._provider = provider

    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        return await self._provider.moderate(message_text, context)


def build_moderator(app_settings: Settings) -> Moderator:
    if app_settings.moderation_provider == "traditional_ml":
        return TraditionalMLModerator()
    return DisabledModerator()


@lru_cache(maxsize=1)
def get_moderation_engine() -> ModerationEngine:
    return ModerationEngine(build_moderator(settings))
