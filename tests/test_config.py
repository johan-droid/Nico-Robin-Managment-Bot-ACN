from __future__ import annotations

import pytest

from src.bot.config import Settings


def test_settings_parse_sudo_users() -> None:
    settings = Settings(BOT_TOKEN="token", SUDO_USERS="1, 2,3")

    assert settings.sudo_users == (1, 2, 3)


def test_settings_parse_commander_ids() -> None:
    settings = Settings(BOT_TOKEN="token", COMMANDER_IDS="10,20")

    assert settings.commander_ids == (10, 20)


def test_database_url_is_normalized_for_asyncpg() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        DATABASE_URL="postgres://user:pass@localhost:5432/robin",
    )

    assert settings.database_url.startswith("postgresql://")
    assert settings.async_database_url.startswith("postgresql+asyncpg://")


def test_async_database_url_strips_libpq_query_params() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        DATABASE_URL=(
            "postgresql://user:pass@localhost:5432/robin"
            "?sslmode=require&channel_binding=require"
        ),
    )

    assert "sslmode" not in settings.async_database_url
    assert "channel_binding" not in settings.async_database_url
    assert settings.async_database_ssl_required is True


def test_moderation_provider_openai_alias_disables_provider() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        MODERATION_PROVIDER="openai",
    )

    assert settings.moderation_provider == "disabled"


def test_webhook_path_is_normalized() -> None:
    settings = Settings(BOT_TOKEN="token", WEBHOOK_PATH="telegram/webhook/")

    assert settings.webhook_path == "/telegram/webhook"


def test_is_webhook_mode_uses_bot_mode_override() -> None:
    webhook_settings = Settings(
        BOT_TOKEN="token",
        BOT_MODE="webhook",
        WEBHOOK_URL="https://example.com",
    )
    polling_settings = Settings(BOT_TOKEN="token", BOT_MODE="polling")

    assert webhook_settings.is_webhook_mode is True
    assert polling_settings.is_webhook_mode is False


def test_is_webhook_mode_falls_back_to_render_external_url() -> None:
    settings = Settings(
        BOT_TOKEN="token", WEBHOOK_URL="", RENDER_EXTERNAL_URL="https://nico-robin-bot.onrender.com",
    )

    assert settings.resolved_webhook_url == "https://nico-robin-bot.onrender.com" or settings.resolved_webhook_url == settings.render_external_url
    assert settings.is_webhook_mode is True


def test_webhook_base_url_strips_path_suffix() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        WEBHOOK_URL="https://example.com/webhook",
    )

    assert settings.resolved_webhook_url == "https://example.com/webhook"
    assert settings.webhook_base_url == "https://example.com"


def test_webhook_mode_requires_https_url() -> None:
    with pytest.raises(ValueError):
        Settings(
            BOT_TOKEN="token",
            BOT_MODE="webhook",
            WEBHOOK_URL="http://example.com",
        )
