from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from telegram.error import TelegramError

from src.bot.config import Settings
from src.bot.services.crypto_service import CryptoService
from src.bot.services.note_service import NoteService
from src.bot.utils.decorators import admin_only, bot_rights_required
from src.bot.utils.logging import _mask_secret_text, _mask_sensitive_data

FERNET_KEY = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="


class DummyMessage:
    def __init__(self) -> None:
        self.text = "/test"
        self.sender_chat = None
        self.from_user = SimpleNamespace(id=123)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs) -> None:
        del kwargs
        self.replies.append(text)


class DummyContext:
    def __init__(self) -> None:
        self.args: list[str] = []
        self.bot = SimpleNamespace()


def test_settings_accept_traditional_ml_provider() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        MODERATION_PROVIDER="traditional_ml",
        DATA_ENCRYPTION_KEY=FERNET_KEY,
    )

    assert settings.moderation_provider == "traditional_ml"


def test_settings_require_encryption_key_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(BOT_TOKEN="token", ENVIRONMENT="production")


def test_note_name_validator_accepts_expected_values() -> None:
    assert NoteService.validate_note_name("archive_123") == "archive_123"


@pytest.mark.parametrize(
    "invalid_name",
    ["../secret", "with space", "semi;colon", "x" * 33],
)
def test_note_name_validator_rejects_invalid_values(invalid_name: str) -> None:
    assert NoteService.validate_note_name(invalid_name) is None


def test_crypto_service_encrypts_and_decrypts_text() -> None:
    service = CryptoService(FERNET_KEY)
    encrypted = service.encrypt_text("Robin keeps the archive tidy.")

    assert encrypted != "Robin keeps the archive tidy."
    assert service.decrypt_text(encrypted) == "Robin keeps the archive tidy."


def test_secret_masking_redacts_urls_and_keys() -> None:
    masked = _mask_sensitive_data(
        {
            "bot_token": "123456:ABCDEFGHIJKLMNOPQRSTUVWX",
            "nested": {"database_url": "postgresql://user:pass@db:5432/name"},
            "text": "redis://localhost:6379/0",
        }
    )

    assert masked["bot_token"] == "[redacted]"
    assert masked["nested"]["database_url"] == "[redacted]"
    assert masked["text"] == "[redacted]"
    assert (
        _mask_secret_text("token 123456:ABCDEFGHIJKLMNOPQRSTUVWX") == "token [redacted]"
    )


@pytest.mark.asyncio
async def test_admin_only_rejects_anonymous_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    message.sender_chat = SimpleNamespace(id=-100)
    message.from_user = None
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=-1000),
        effective_message=message,
    )
    context = DummyContext()
    called = False

    async def fake_log_event(**kwargs) -> None:
        del kwargs

    async def handler(update, context) -> None:
        del update, context
        nonlocal called
        called = True

    monkeypatch.setattr(
        "src.bot.utils.decorators.SecurityLogger.log_event",
        fake_log_event,
    )

    wrapped = admin_only(handler)
    await wrapped(update, context)

    assert called is False
    assert message.replies


@pytest.mark.asyncio
async def test_admin_only_fails_closed_on_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=-1000),
        effective_message=message,
    )
    context = DummyContext()
    called = False

    async def fake_is_admin(*args, **kwargs) -> bool:
        del args, kwargs
        raise TelegramError("boom")

    async def fake_log_event(**kwargs) -> None:
        del kwargs

    async def handler(update, context) -> None:
        del update, context
        nonlocal called
        called = True

    monkeypatch.setattr("src.bot.utils.decorators.is_telegram_admin", fake_is_admin)
    monkeypatch.setattr(
        "src.bot.utils.decorators.SecurityLogger.log_event",
        fake_log_event,
    )

    wrapped = admin_only(handler)
    await wrapped(update, context)

    assert called is False
    assert message.replies


@pytest.mark.asyncio
async def test_bot_rights_required_blocks_without_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=-1000),
        effective_message=message,
    )
    context = DummyContext()
    called = False

    async def fake_log_event(**kwargs) -> None:
        del kwargs

    async def fake_has_rights(*args, **kwargs) -> bool:
        del args, kwargs
        return False

    async def handler(update, context) -> None:
        del update, context
        nonlocal called
        called = True

    monkeypatch.setattr(
        "src.bot.utils.decorators.SecurityLogger.log_event",
        fake_log_event,
    )
    monkeypatch.setattr(
        "src.bot.utils.decorators.bot_has_admin_rights",
        fake_has_rights,
    )

    wrapped = bot_rights_required("can_delete_messages")(handler)
    await wrapped(update, context)

    assert called is False
    assert message.replies
