from __future__ import annotations

from types import SimpleNamespace

import pytest
from telegram.error import TelegramError

from src.bot.services.broadcast_service import BroadcastService


class FakeBot:
    def __init__(self) -> None:
        self.copy_attempts = 0
        self.edit_text_calls: list[dict] = []
        self.edit_caption_calls: list[dict] = []

    async def copy_message(self, chat_id: int, from_chat_id: int, message_id: int):
        self.copy_attempts += 1
        if self.copy_attempts < 3:
            raise TelegramError("temporary broadcast failure")
        return SimpleNamespace(message_id=9000 + chat_id)

    async def edit_message_text(self, **kwargs):
        self.edit_text_calls.append(kwargs)
        return True

    async def edit_message_caption(self, **kwargs):
        self.edit_caption_calls.append(kwargs)
        return True


@pytest.mark.asyncio
async def test_broadcast_retries_failed_group(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = FakeBot()
    context = SimpleNamespace(bot=bot)
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-1001),
        message_id=21,
        text="Channel update",
        caption=None,
    )

    async def fake_get_main_acn_groups() -> list[int]:
        return [101]

    monkeypatch.setattr(
        BroadcastService,
        "get_main_acn_groups",
        staticmethod(fake_get_main_acn_groups),
    )

    stats = await BroadcastService.broadcast_to_main_groups(
        context,
        message,
        "Channel One",
        "announcement",
    )

    assert stats["successful"] == 1
    assert stats["failed"] == 0
    assert stats["deliveries"][0]["group_id"] == 101
    assert bot.copy_attempts == 3


@pytest.mark.asyncio
async def test_handle_channel_post_deduplicates_repeat_message(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    async def fake_broadcast(*args, **kwargs):
        calls.append(True)
        return {"successful": 1, "failed": 0, "errors": [], "deliveries": []}

    async def fake_is_acn_channel(channel_id: int) -> bool:
        return True

    async def fake_get_channel_state(session, channel_id):
        return SimpleNamespace(last_forwarded_message_id=55)

    monkeypatch.setattr(
        BroadcastService,
        "_get_channel_state",
        staticmethod(fake_get_channel_state),
    )
    monkeypatch.setattr(BroadcastService, "is_acn_channel", staticmethod(fake_is_acn_channel))
    monkeypatch.setattr(BroadcastService, "broadcast_to_main_groups", fake_broadcast)

    update = SimpleNamespace(
        channel_post=SimpleNamespace(
            chat=SimpleNamespace(id=-1001, title="Channel One"),
            message_id=55,
            text="Duplicate",
            caption=None,
        )
    )

    result = await BroadcastService.handle_channel_post(update, SimpleNamespace(bot=SimpleNamespace()))

    assert result is True
    assert calls == []


@pytest.mark.asyncio
async def test_handle_channel_edited_post_updates_copied_message(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = FakeBot()
    context = SimpleNamespace(bot=bot)
    delivery = SimpleNamespace(destination_group_id=101, destination_message_id=9001)

    async def fake_is_acn_channel(channel_id: int) -> bool:
        return True

    async def fake_get_deliveries_for_source(session, channel_id, message_id):
        return [delivery]

    monkeypatch.setattr(
        BroadcastService,
        "_get_deliveries_for_source",
        staticmethod(fake_get_deliveries_for_source),
    )
    monkeypatch.setattr(BroadcastService, "is_acn_channel", staticmethod(fake_is_acn_channel))

    update = SimpleNamespace(
        edited_channel_post=SimpleNamespace(
            chat=SimpleNamespace(id=-1001, title="Channel One"),
            message_id=21,
            text="Edited channel text",
            caption=None,
            entities=None,
            caption_entities=None,
        )
    )

    result = await BroadcastService.handle_channel_edited_post(update, context)

    assert result is True
    assert len(bot.edit_text_calls) == 1
    assert bot.edit_text_calls[0]["chat_id"] == 101
    assert bot.edit_text_calls[0]["message_id"] == 9001
    assert bot.edit_text_calls[0]["text"] == "Edited channel text"
