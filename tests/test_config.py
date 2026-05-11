from __future__ import annotations

from config import Settings


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
