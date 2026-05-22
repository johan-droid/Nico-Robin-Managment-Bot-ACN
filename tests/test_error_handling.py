from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.bot.utils import decorators as decorators_module
from src.bot.bot.middleware import error_handler as error_module
from src.bot.utils.decorators import log_command


class FakeMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeBot:
    def __init__(self) -> None:
        self.sent_messages: list[dict] = []

    async def send_message(self, **kwargs):
        self.sent_messages.append(kwargs)


@pytest.mark.asyncio
async def test_log_command_logs_and_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    logged: list[dict] = []

    def fake_error(*args, **kwargs):
        logged.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr(decorators_module.logger, "error", fake_error)

    @log_command
    async def boom(update, context) -> None:
        raise RuntimeError("broken command")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100),
        effective_user=SimpleNamespace(id=7),
        effective_message=SimpleNamespace(text="/boom test", caption=None),
    )
    context = SimpleNamespace(bot=SimpleNamespace())

    with pytest.raises(RuntimeError, match="broken command"):
        await boom(update, context)

    assert logged
    assert logged[0]["kwargs"]["command"] == "boom"
    assert logged[0]["kwargs"]["callback"] == "boom"
    assert "traceback" in logged[0]["kwargs"]


@pytest.mark.asyncio
async def test_error_handler_logs_and_notifies_private_group(monkeypatch: pytest.MonkeyPatch) -> None:
    logged: list[dict] = []

    def fake_error(*args, **kwargs):
        logged.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr(error_module.logger, "error", fake_error)
    monkeypatch.setattr(error_module.settings, "log_channel_id", -999_001)

    bot = FakeBot()
    ctx = SimpleNamespace(bot=bot, error=ValueError("kaboom"))
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=7),
        effective_chat=SimpleNamespace(id=-100),
        effective_message=FakeMessage(),
    )

    await error_module.error_handler(update, ctx)

    assert logged
    assert any(entry["kwargs"].get("traceback") for entry in logged)
    assert bot.sent_messages
    assert bot.sent_messages[0]["chat_id"] == -999_001
    assert "kaboom" in bot.sent_messages[0]["text"]
