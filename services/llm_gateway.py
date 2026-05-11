from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from typing import Literal, Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from config import Settings, settings

try:
    from profanity_check import predict_prob

    PROFANITY_CHECK_AVAILABLE = True
except ImportError:
    predict_prob = None
    PROFANITY_CHECK_AVAILABLE = False

# Import swear word service for integration
try:
    from services.swear_word_service import SwearWordService

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

MODERATION_SYSTEM_PROMPT = (
    "You are the moderation brain for Nico Robin, a Telegram group management bot. "
    "Return only JSON with keys score, category, action, and rationale. "
    "Categories: hate_speech, harassment, nsfw_text, doxxing, spam_promo, "
    "self_harm, safe. Actions: none, warn, delete, ban, notify_admin, "
    "delete_warn. Prefer the least severe action that protects the group."
)


class ModerationResult(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    category: str = "safe"
    action: ModerationAction = "none"
    rationale: str | None = None

    @classmethod
    def safe(cls) -> ModerationResult:
        return cls(score=0.0, category="safe", action="none")


class LLMProvider(Protocol):
    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        """Return a moderation decision for a message."""


class DisabledProvider:
    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        del message_text, context
        return ModerationResult.safe()


class TraditionalMLProvider:
    def __init__(self) -> None:
        # Pre-compile regex patterns for performance
        self.doxxing_patterns = [
            re.compile(
                r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", re.IGNORECASE
            ),  # Phone numbers
            re.compile(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.IGNORECASE
            ),  # Emails
            re.compile(
                r"\b\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Place|Pl)\b",
                re.IGNORECASE,
            ),  # Addresses
        ]

        self.spam_patterns = [
            re.compile(r"https?://[^\s]+", re.IGNORECASE),  # URLs
            re.compile(r"www\.[^\s]+", re.IGNORECASE),  # URLs without protocol
            re.compile(
                r"\b(buy|sell|discount|offer|deal|free|win|prize|click|visit|check out|limited time)\b",
                re.IGNORECASE,
            ),  # Promotional words
            re.compile(r"\b\$\d+\.?\d*\b", re.IGNORECASE),  # Prices
        ]

        self.self_harm_patterns = [
            re.compile(
                r"\b(kill|die|suicide|end my life|hurt myself|self.harm|cutting|overdose)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(want to die|don.t want to live|better off dead)\b", re.IGNORECASE
            ),
        ]

        # Performance optimization: quick checks for safe content
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
        self.max_content_length = 10000  # Prevent processing extremely long messages

    def _detect_doxxing(self, text: str) -> float:
        score = 0.0
        for pattern in self.doxxing_patterns:
            if pattern.search(text):
                score = max(score, 0.8)
                # Early exit if high confidence doxxing detected
                if score >= 0.8:
                    return score
        return score

    def _detect_spam(self, text: str) -> float:
        score = 0.0
        matches = 0
        for pattern in self.spam_patterns:
            if pattern.search(text):
                matches += 1
                # Early exit for high confidence spam
                if matches >= 2:
                    return 0.7
        if matches == 1:
            score = 0.5
        return score

    def _detect_self_harm(self, text: str) -> float:
        score = 0.0
        for pattern in self.self_harm_patterns:
            if pattern.search(text):
                score = max(score, 0.9)
                # Early exit for self-harm (highest priority)
                if score >= 0.9:
                    return score
        return score

    def _map_probability_to_category(self, prob: float) -> tuple[str, ModerationAction]:
        if prob < 0.3:
            return "safe", "none"
        elif prob < 0.5:
            return "harassment", "warn"
        elif prob < 0.7:
            return "hate_speech", "delete"
        elif prob < 0.9:
            return "nsfw_text", "delete_warn"
        else:
            return "hate_speech", "ban"

    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        # Performance optimization: skip very long messages
        if len(message_text) > self.max_content_length:
            return ModerationResult.safe()

        # Performance optimization: quick safe content check
        text_lower = message_text.lower().strip()
        if text_lower in self.safe_indicators or text_lower.startswith(
            tuple(self.safe_indicators)
        ):
            return ModerationResult.safe()

        # Check for specific patterns first (always available)
        doxxing_score = self._detect_doxxing(message_text)
        spam_score = self._detect_spam(message_text)
        self_harm_score = self._detect_self_harm(message_text)

        # Check for swear words if service is available
        swear_word_score = 0.0
        swear_word_category = None
        if SWEAR_WORD_SERVICE_AVAILABLE and context.get("group_id"):
            try:
                from database import async_session_factory

                async with async_session_factory() as session:
                    matches = await SwearWordService.match_swear_words(
                        session, context["group_id"], message_text
                    )
                    if matches:
                        # Use highest severity match
                        highest_match = max(
                            matches,
                            key=lambda m: (
                                0
                                if m.severity == "mild"
                                else 1
                                if m.severity == "moderate"
                                else 2
                            ),
                        )
                        swear_word_score = (
                            0.9 if highest_match.severity == "severe" else 0.7
                        )
                        swear_word_category = f"swear_word_{highest_match.severity}"
            except Exception:
                # Continue without swear word checking if there's an error
                pass

        # Handle high-priority detections first
        if self_harm_score >= 0.9:
            return ModerationResult(
                score=self_harm_score,
                category="self_harm",
                action="notify_admin",
                rationale="Self-harm content detected",
            )
        elif doxxing_score >= 0.8:
            return ModerationResult(
                score=doxxing_score,
                category="doxxing",
                action="delete_warn",
                rationale="Personal information detected",
            )
        elif spam_score >= 0.7:
            return ModerationResult(
                score=spam_score,
                category="spam_promo",
                action="delete",
                rationale="Spam or promotional content detected",
            )
        elif swear_word_score >= 0.7:
            # Handle swear word detection
            action = (
                "delete_warn"
                if swear_word_category and "severe" in swear_word_category
                else "warn"
            )
            return ModerationResult(
                score=swear_word_score,
                category=swear_word_category or "swear_word_moderate",
                action=action,
                rationale="Swear word detected",
            )

        # Use SVM for general toxicity if available
        toxicity_prob = 0.0
        if PROFANITY_CHECK_AVAILABLE and predict_prob is not None:
            try:
                toxicity_prob = float(predict_prob([message_text])[0])
            except Exception:
                # Log error but don't fail completely
                toxicity_prob = 0.0

        # Use the highest score from all detections
        max_score = max(
            toxicity_prob, doxxing_score, spam_score, self_harm_score, swear_word_score
        )

        # If no library and no patterns detected, return safe
        if not PROFANITY_CHECK_AVAILABLE and max_score < 0.5:
            return ModerationResult.safe()

        # Use general toxicity detection for remaining cases
        category, action = self._map_probability_to_category(max_score)
        rationale = f"Traditional ML detection: {category}"
        if not PROFANITY_CHECK_AVAILABLE:
            rationale += " (regex-only mode)"

        return ModerationResult(
            score=max_score, category=category, action=action, rationale=rationale
        )


class OpenAIChatProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": MODERATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"message": message_text, "context": dict(context)},
                        ensure_ascii=False,
                    ),
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=180,
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        action = str(payload.get("action", "none")).replace(" + ", "_")
        payload["action"] = action
        return ModerationResult.model_validate(payload)


class LLMGateway:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def moderate(
        self,
        message_text: str,
        context: Mapping[str, object],
    ) -> ModerationResult:
        return await self._provider.moderate(message_text, context)


def build_provider(app_settings: Settings) -> LLMProvider:
    if app_settings.llm_provider == "openai" and app_settings.openai_api_key:
        return OpenAIChatProvider(
            api_key=app_settings.openai_api_key,
            model=app_settings.openai_moderation_model,
        )
    elif app_settings.llm_provider == "traditional_ml":
        return TraditionalMLProvider()
    return DisabledProvider()


@lru_cache(maxsize=1)
def get_llm_gateway() -> LLMGateway:
    return LLMGateway(build_provider(settings))
