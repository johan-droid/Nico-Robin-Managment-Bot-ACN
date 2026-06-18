from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.bot.bot.plugins import flood_control


class _Message:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_kwargs) -> None:
        self.replies.append(text)


class _Bot:
    async def get_chat_member(self, _chat_id: int, _user_id: int):
        return SimpleNamespace(status="member")


@pytest.mark.asyncio
async def test_flood_toggle_requires_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    touched_database = False

    async def fail_if_called(*_args, **_kwargs) -> None:
        nonlocal touched_database
        touched_database = True

    monkeypatch.setattr(flood_control.GroupService, "ensure_group", fail_if_called)

    message = _Message()
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=-100, type="supergroup"),
        effective_user=SimpleNamespace(id=123),
    )
    context = SimpleNamespace(bot=_Bot(), args=["off"])

    await flood_control.flood(update, context)

    assert touched_database is False
    assert len(message.replies) == 1
    assert "Access denied" in message.replies[0]
