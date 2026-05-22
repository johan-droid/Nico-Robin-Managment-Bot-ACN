from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.bot.utils import decorators as decorator_utils
from src.bot.utils.decorators import (
    BotPermissionError,
    feature_enabled,
    is_admin,
    require_admin,
    require_captain_commander,
)


class FakeMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeBot:
    def __init__(self, bot_status: str, bot_can_restrict: bool, user_status: str) -> None:
        self.id = 99
        self._bot_status = bot_status
        self._bot_can_restrict = bot_can_restrict
        self._user_status = user_status

    async def get_chat_member(self, chat_id: int, user_id: int):
        if user_id == self.id:
            return SimpleNamespace(
                status=self._bot_status,
                can_restrict_members=self._bot_can_restrict,
            )
        return SimpleNamespace(status=self._user_status)


class FakeFeatureBot(FakeBot):
    async def get_chat_member(self, chat_id: int, user_id: int):
        return await super().get_chat_member(chat_id, user_id)


@pytest.mark.asyncio
async def test_is_admin_accepts_admin_user() -> None:
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100),
        effective_user=SimpleNamespace(id=7),
    )
    context = SimpleNamespace(bot=FakeBot("administrator", True, "creator"))

    assert await is_admin(update, context) is True


@pytest.mark.asyncio
async def test_is_admin_rejects_non_admin_user() -> None:
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100),
        effective_user=SimpleNamespace(id=7),
    )
    context = SimpleNamespace(bot=FakeBot("administrator", True, "member"))

    assert await is_admin(update, context) is False


@pytest.mark.asyncio
async def test_is_admin_raises_when_bot_lacks_moderation_rights() -> None:
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100),
        effective_user=SimpleNamespace(id=7),
    )
    context = SimpleNamespace(bot=FakeBot("administrator", False, "administrator"))

    with pytest.raises(BotPermissionError, match="can_restrict_members"):
        await is_admin(update, context)


@pytest.mark.asyncio
async def test_require_admin_blocks_non_admin_with_friendly_message() -> None:
    calls: list[bool] = []

    @require_admin
    async def protected(update, context) -> None:
        calls.append(True)

    message = FakeMessage()
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100),
        effective_user=SimpleNamespace(id=7),
        effective_message=message,
    )
    context = SimpleNamespace(bot=FakeBot("administrator", True, "member"))

    await protected(update, context)

    assert calls == []
    assert message.replies == ["🌸 \"Interesting... but you lack the authority.\" — Robin"]


@pytest.mark.asyncio
async def test_feature_enabled_blocks_disabled_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_is_enabled(group_id: int, feature_name: str, user_id: int | None = None) -> bool:
        return False

    monkeypatch.setattr(
        decorator_utils.FeatureService,
        "is_feature_enabled",
        fake_is_enabled,
    )

    calls: list[bool] = []

    @feature_enabled("moderation")
    async def protected(update, context) -> None:
        calls.append(True)

    message = FakeMessage()
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100),
        effective_user=SimpleNamespace(id=7),
        effective_message=message,
    )
    context = SimpleNamespace(bot=FakeBot("administrator", True, "member"))

    await protected(update, context)

    assert calls == []
    assert message.replies == ["🌸 This feature is disabled for this group."]


@pytest.mark.asyncio
async def test_feature_enabled_allows_enabled_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_is_enabled(group_id: int, feature_name: str, user_id: int | None = None) -> bool:
        return True

    monkeypatch.setattr(
        decorator_utils.FeatureService,
        "is_feature_enabled",
        fake_is_enabled,
    )

    calls: list[bool] = []

    @feature_enabled("moderation")
    async def protected(update, context) -> None:
        calls.append(True)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100),
        effective_user=SimpleNamespace(id=7),
        effective_message=FakeMessage(),
    )
    context = SimpleNamespace(bot=FakeBot("administrator", True, "member"))

    await protected(update, context)

    assert calls == [True]


@pytest.mark.asyncio
async def test_require_captain_commander_blocks_other_users(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_is_captain(user_id: int) -> bool:
        return False

    async def fake_is_commander(user_id: int) -> bool:
        return False

    monkeypatch.setattr(decorator_utils.ACNService, "is_captain", fake_is_captain)
    monkeypatch.setattr(decorator_utils.ACNService, "is_commander", fake_is_commander)

    calls: list[bool] = []

    @require_captain_commander
    async def protected(update, context) -> None:
        calls.append(True)

    message = FakeMessage()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=7),
        effective_message=message,
    )
    context = SimpleNamespace(bot=FakeBot("administrator", True, "member"))

    await protected(update, context)

    assert calls == []
    assert message.replies == ["🌸 Only the captain or commanders can change feature settings."]