from __future__ import annotations

from src.bot.bot.app import create_application
from src.bot.config import Settings


def test_application_registers_security_middleware_groups() -> None:
    application = create_application(Settings(BOT_TOKEN="token"))

    assert -3 in application.handlers
    assert -2 in application.handlers
    assert -1 in application.handlers
    assert 0 in application.handlers
    assert 1 in application.handlers
