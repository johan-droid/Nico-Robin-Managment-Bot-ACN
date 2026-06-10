from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import src.bot.main as bot_main


class _DummyBot:
    def __init__(self) -> None:
        self.commands_set = False
        self.webhook_deleted = False

    async def set_my_commands(self, _commands) -> None:
        self.commands_set = True

    async def delete_webhook(self, **_kwargs) -> None:
        self.webhook_deleted = True

    async def set_webhook(self, **_kwargs) -> None:
        return None

    async def get_webhook_info(self):
        return SimpleNamespace(
            pending_update_count=0,
            last_error_date=None,
            last_error_message=None,
            ip_address=None,
        )


class _DummyUpdater:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def start_polling(self, **_kwargs) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


class _DummyApplication:
    def __init__(self) -> None:
        self.bot = _DummyBot()
        self.updater = _DummyUpdater()
        self.started = False
        self.stopped = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


@pytest.mark.asyncio
async def test_polling_mode_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _DummyApplication()

    async def noop(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(bot_main, "_wait_for_db", noop)
    monkeypatch.setattr(bot_main, "_auto_migrate", noop)
    monkeypatch.setattr(bot_main, "dispose_engine", noop)
    monkeypatch.setattr(bot_main, "create_application", lambda _settings: app)

    run_task = asyncio.create_task(bot_main._polling_mode())
    await asyncio.sleep(0)
    run_task.cancel()
    await run_task

    assert app.started is True
    assert app.stopped is True
    assert app.bot.commands_set is True
    assert app.bot.webhook_deleted is True
    assert app.updater.started is True
    assert app.updater.stopped is True


@pytest.mark.asyncio
async def test_webhook_mode_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _DummyApplication()
    observed: dict[str, bool] = {"served": False}

    class _DummyServer:
        def __init__(self, _config) -> None:
            return None

        async def serve(self) -> None:
            observed["served"] = True

    async def noop(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(bot_main, "_wait_for_db", noop)
    monkeypatch.setattr(bot_main, "_auto_migrate", noop)
    monkeypatch.setattr(bot_main, "initialize_websocket_client", noop)
    monkeypatch.setattr(bot_main, "shutdown_websocket_client", noop)
    monkeypatch.setattr(bot_main, "_configure_telegram_webhook", noop)
    monkeypatch.setattr(bot_main, "dispose_engine", noop)
    monkeypatch.setattr(bot_main, "create_application", lambda _settings: app)
    monkeypatch.setattr(bot_main, "create_combined_app", lambda _app: object())
    monkeypatch.setattr(bot_main.uvicorn, "Server", _DummyServer)
    monkeypatch.setattr(bot_main.asyncio, "sleep", noop)

    await bot_main._webhook_mode()

    assert observed["served"] is True
    assert app.started is True
    assert app.stopped is True
    assert app.bot.commands_set is True
