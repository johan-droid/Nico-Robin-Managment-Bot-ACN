from __future__ import annotations

from pathlib import Path

import pytest

from src.bot.services.llm_gateway import DisabledProvider
from src.bot.services.moderation_engine import TraditionalMLModerator


@pytest.mark.asyncio
async def test_disabled_provider_returns_safe_result() -> None:
    result = await DisabledProvider().moderate("hello", {})

    assert result.action == "none"
    assert result.category == "safe"
    assert result.score == 0


@pytest.mark.asyncio
async def test_traditional_moderator_keeps_benign_message_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.bot.services.moderation_engine.predict_prob",
        lambda texts: [0.10 for _ in texts],
    )

    result = await TraditionalMLModerator().moderate("hello there", {"group_id": 123})

    assert result.action == "none"
    assert result.category == "safe"


@pytest.mark.asyncio
async def test_traditional_moderator_maps_probability_thresholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.bot.services.moderation_engine.predict_prob",
        lambda texts: [0.82 for _ in texts],
    )

    result = await TraditionalMLModerator().moderate(
        "you are awful",
        {"group_id": 123},
    )

    assert result.action == "delete_warn"
    assert result.category == "toxicity"
    assert result.score == pytest.approx(0.82)


@pytest.mark.asyncio
async def test_traditional_moderator_detects_self_harm() -> None:
    result = await TraditionalMLModerator().moderate(
        "I want to die tonight",
        {"group_id": 123},
    )

    assert result.action == "notify_admin"
    assert result.category == "self_harm"


@pytest.mark.asyncio
async def test_traditional_moderator_detects_doxxing() -> None:
    result = await TraditionalMLModerator().moderate(
        "Call me at 555-123-4567",
        {"group_id": 123},
    )

    assert result.action == "delete_warn"
    assert result.category == "doxxing"


@pytest.mark.asyncio
async def test_traditional_moderator_detects_spam() -> None:
    result = await TraditionalMLModerator().moderate(
        "Buy now at https://spam.test for a free prize",
        {"group_id": 123},
    )

    assert result.action == "delete"
    assert result.category == "spam_promo"


def test_llm_gateway_shim_contains_no_openai_import() -> None:
    gateway_source = Path("src/bot/services/llm_gateway.py").read_text(encoding="utf-8")

    assert "openai" not in gateway_source.lower()
