from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.bot.bot.plugins import welcome
from src.bot.utils import decorators


class _Message:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.from_user = SimpleNamespace(id=123)
        self.sender_chat = None
        self.text = "/resetwelcome"

    async def reply_text(self, text: str, **_kwargs) -> None:
        self.replies.append(text)


class _Bot:
    id = 999

    async def get_chat_member(self, chat_id: int, user_id: int):
        del chat_id
        if user_id == self.id:
            return SimpleNamespace(status="administrator", can_restrict_members=True)
        return SimpleNamespace(status="member")


@pytest.mark.asyncio
async def test_resetwelcome_requires_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    touched_database = False

    async def fail_if_called(*_args, **_kwargs) -> None:
        nonlocal touched_database
        touched_database = True

    async def noop_log_event(**_kwargs) -> None:
        return None

    monkeypatch.setattr(welcome.GroupService, "ensure_group", fail_if_called)
    monkeypatch.setattr(decorators.SecurityLogger, "log_event", noop_log_event)

    message = _Message()
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=-100, type="supergroup"),
        effective_user=SimpleNamespace(id=123),
    )
    context = SimpleNamespace(bot=_Bot())

    await welcome.resetwelcome(update, context)

    assert touched_database is False
    assert len(message.replies) == 1
    assert "authority" in message.replies[0]
