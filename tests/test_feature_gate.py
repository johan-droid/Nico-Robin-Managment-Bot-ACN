from __future__ import annotations

import pytest
from telegram import Update, Message, Chat, User
from telegram.ext import ApplicationHandlerStop

from src.bot.bot.middleware.feature_gate import feature_gate_check
from src.bot.services.feature_service import FeatureService

class FakeMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)

class FakeUpdate(Update):
    def __init__(self, message) -> None:
        self._message = message

    @property
    def effective_message(self):
        return self._message

    @property
    def effective_chat(self):
        return Chat(id=-100, type="supergroup")

    @property
    def effective_user(self):
        return User(id=7, first_name="Test", is_bot=False)

@pytest.mark.asyncio
async def test_feature_gate_blocks_disabled_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_can_use_feature(*args, **kwargs) -> tuple[bool, str]:
        return False, "Feature is disabled"

    monkeypatch.setattr(FeatureService, "can_use_feature", fake_can_use_feature)

    message = FakeMessage(text="/ban user")
    update = FakeUpdate(message)
    context = {}

    with pytest.raises(ApplicationHandlerStop):
        await feature_gate_check(update, context)

    assert message.replies == ["🚫 Feature is disabled"]

@pytest.mark.asyncio
async def test_feature_gate_allows_enabled_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_can_use_feature(*args, **kwargs) -> tuple[bool, str]:
        return True, ""

    monkeypatch.setattr(FeatureService, "can_use_feature", fake_can_use_feature)

    message = FakeMessage(text="/ban user")
    update = FakeUpdate(message)
    context = {}

    # Should not raise any exception
    await feature_gate_check(update, context)
    assert message.replies == []
