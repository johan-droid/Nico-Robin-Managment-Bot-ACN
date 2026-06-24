from __future__ import annotations

from types import SimpleNamespace

import pytest
from telegram.ext import CommandHandler

from src.bot.bot import dispatcher
from src.bot.bot.app import create_application
from src.bot.config import Settings


def _registered_commands(application) -> list[str]:
    commands: list[str] = []
    for handlers in application.handlers.values():
        for handler in handlers:
            if isinstance(handler, CommandHandler):
                commands.extend(handler.commands)
    return commands


def test_application_registers_security_middleware_groups() -> None:
    application = create_application(Settings(BOT_TOKEN="token"))

    assert -3 in application.handlers
    assert -2 in application.handlers
    assert -1 in application.handlers
    assert 0 in application.handlers
    assert 1 in application.handlers


def test_application_does_not_register_duplicate_commands() -> None:
    application = create_application(Settings(BOT_TOKEN="token"))
    commands = _registered_commands(application)

    duplicates = sorted(
        {command for command in commands if commands.count(command) > 1}
    )

    assert duplicates == []


def test_application_registers_documented_pdf_commands() -> None:
    application = create_application(Settings(BOT_TOKEN="token"))
    commands = set(_registered_commands(application))

    # We only check for a subset of core commands that are guaranteed to be in COMMAND_BINDINGS
    documented_commands = {
        "start",
        "help",
        "ping",
        "ban",
        "mute",
        "warn",
        "filter",
        "filters",
        "welcome",
        "notes",
        "lock",
        "locks",
        "flood",
        "addswear",
        "purgechannels",
    }

    assert documented_commands <= commands


def test_dispatcher_registers_command_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_register_command_handlers(app) -> None:
        nonlocal called
        called = True
        del app

    def fake_import_module(name: str):
        del name
        return SimpleNamespace(register=lambda app: None)

    monkeypatch.setattr(
        dispatcher, "register_command_handlers", fake_register_command_handlers
    )
    monkeypatch.setattr(dispatcher, "import_module", fake_import_module)

    app = SimpleNamespace(add_handler=lambda *args, **kwargs: None)

    dispatcher.register_all_handlers(app)

    assert called is True
