from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import structlog
import uvicorn
from telegram import BotCommand

from src.bot.bot.app import create_application
from src.bot.bot.handlers_list import COMMAND_BINDINGS
from src.bot.client.websocket_client import (
    initialize_websocket_client,
    shutdown_websocket_client,
)
from src.bot.config import settings
from src.bot.database import dispose_engine, engine
from src.bot.gateway.webhook import create_combined_app
from src.bot.utils.logging import configure_logging

logger = structlog.get_logger(__name__)

_BOT_LOCK_HANDLE = None
_BOT_COMMAND_MENU_LIMIT = 100
_ALLOWED_UPDATES = [
    "message",
    "edited_message",
    "channel_post",
    "edited_channel_post",
    "callback_query",
    "chat_member",
    "my_chat_member",
]


def _log_robin_banner(mode: str) -> None:
    """Emit a small Robin-style ready banner in the logs."""
    banner_lines = [
        r"  /\_/\\",
        r" ( .. )  Nico Robin Bot",
        r" / > < \  backend ready",
    ]
    logger.info("robin_ready_banner", mode=mode, banner=" | ".join(banner_lines))


def _acquire_single_instance_lock() -> None:
    """Prevent multiple bot processes from running at the same time."""
    global _BOT_LOCK_HANDLE

    lock_path = Path("logs") / "nico_robin.lock"
    lock_path.parent.mkdir(exist_ok=True)
    lock_handle = open(lock_path, "a+b")

    try:
        if os.name == "nt":
            import msvcrt

            lock_handle.seek(0)
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1024)
        else:
            import fcntl

            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception as e:
        try:
            lock_handle.close()
        except OSError:
            pass
        logger.error("bot_already_running", lock_file=str(lock_path))
        raise SystemExit(1) from e

    _BOT_LOCK_HANDLE = lock_handle


_BOT_COMMAND_MENU_LIMIT = 100


def _get_menu_commands() -> list[BotCommand]:
    menu = []
    for binding in COMMAND_BINDINGS:
        if binding.show_in_main_menu:
            menu.append(
                BotCommand(binding.command, binding.description or binding.command)
            )
    return menu[:_BOT_COMMAND_MENU_LIMIT]


async def _set_command_menu(application) -> None:
    """Register the generated slash-command menu with Telegram."""
    command_menu = _get_menu_commands()
    await application.bot.set_my_commands(command_menu)
    logger.info(
        "bot_command_menu_configured",
        command_count=len(command_menu),
    )


async def _wait_for_db() -> None:
    """Wait for the database to be ready before starting."""
    retries = 5
    from sqlalchemy import text

    while retries > 0:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("database_connection_successful")
            return
        except Exception as e:
            retries -= 1
            error_text = str(e) or e.__class__.__name__
            logger.warning(
                "database_connection_failed", retries_left=retries, error=error_text
            )
            await engine.dispose()
            if retries == 0:
                logger.error("database_connection_exhausted")
                sys.exit(1)
            await asyncio.sleep(2.0)


async def _auto_migrate() -> None:
    """Run Alembic migrations automatically on startup."""
    if not getattr(
        settings, "auto_migrate_on_startup", settings.environment != "production"
    ):
        logger.info("database_auto_migration_disabled")
        return

    try:
        import asyncio

        from alembic import command as alembic_cmd
        from alembic.config import Config as AlembicConfig
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS alembic_version ("
                    "version_num VARCHAR(128) NOT NULL PRIMARY KEY)"
                )
            )
            result = await conn.execute(
                text(
                    "SELECT character_maximum_length "
                    "FROM information_schema.columns "
                    "WHERE table_schema='public' "
                    "AND table_name='alembic_version' "
                    "AND column_name='version_num'"
                )
            )
            current_length = result.scalar_one_or_none()
            if current_length is None or current_length < 128:
                await conn.execute(
                    text(
                        "ALTER TABLE alembic_version "
                        "ALTER COLUMN version_num TYPE VARCHAR(128)"
                    )
                )
                # DDL can invalidate prepared plans in existing pooled connections.
                await engine.dispose()

        def run_upgrade():
            cfg = AlembicConfig("alembic.ini")
            alembic_cmd.upgrade(cfg, "head")

        # Run the sync Alembic commands in a threadpool to avoid blocking the event loop
        await asyncio.to_thread(run_upgrade)
        logger.info("database_migrated_successfully")
    except Exception as exc:
        logger.error("database_migration_failed", error=str(exc))
        raise


def _resolve_webhook_target_url() -> str:
    """Build the exact webhook URL Telegram should call."""
    base_url = settings.webhook_base_url.rstrip("/")
    webhook_path = settings.webhook_path
    if not webhook_path.startswith("/"):
        webhook_path = f"/{webhook_path}"
    target = f"{base_url}{webhook_path}"
    if settings.webhook_path_token:
        target = f"{target.rstrip('/')}/{settings.webhook_path_token}"
    return target


async def _configure_telegram_webhook(ptb_app) -> None:
    """Set and verify Telegram webhook configuration."""
    webhook_url = _resolve_webhook_target_url()
    parsed = urlsplit(webhook_url)
    if parsed.scheme.lower() != "https":
        raise RuntimeError(
            f"Webhook mode requires an HTTPS webhook URL. Resolved URL: {webhook_url!r}"
        )

    await ptb_app.bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret or None,
        drop_pending_updates=settings.webhook_drop_pending_updates,
        allowed_updates=_ALLOWED_UPDATES,
    )
    webhook_info = await ptb_app.bot.get_webhook_info()
    logger.info(
        "telegram_webhook_configured",
        url=webhook_url,
        pending_update_count=webhook_info.pending_update_count,
        last_error_date=webhook_info.last_error_date,
        last_error_message=webhook_info.last_error_message,
        ip_address=webhook_info.ip_address,
    )


async def _webhook_mode() -> None:
    """Run bot in webhook mode with ASGI server."""
    logger.info(
        "bot_mode",
        mode="webhook",
        webhook_url=settings.resolved_webhook_url,
        webhook_path=settings.webhook_path,
    )

    await _wait_for_db()
    try:
        await _auto_migrate()
    except Exception as exc:
        logger.warning("database_auto_migrate_skipped", error=str(exc))

    ptb_app = create_application(settings)
    web_app = create_combined_app(ptb_app)
    server_config = uvicorn.Config(
        web_app,
        host="0.0.0.0",
        port=settings.port,
        log_level="info",
        loop="asyncio",
        log_config=None,
    )
    server = uvicorn.Server(server_config)

    async with ptb_app:
        await ptb_app.start()
        await _set_command_menu(ptb_app)
        server_task = asyncio.create_task(server.serve())
        await asyncio.sleep(2.0)

        await initialize_websocket_client(ptb_app)

        await _configure_telegram_webhook(ptb_app)

        logger.info("nico_robin_started", port=settings.port)
        _log_robin_banner("webhook")

        if settings.websocket_enabled:
            logger.info("websocket_enabled", port=settings.port)

        try:
            await server_task
        finally:
            await shutdown_websocket_client()
            await ptb_app.stop()
            await dispose_engine()
            logger.info("nico_robin_stopped")


async def _polling_mode() -> None:
    """Run bot in polling mode without relying on PTB's loop management."""
    logger.info("bot_mode", mode="polling")

    await _wait_for_db()
    try:
        await _auto_migrate()
    except Exception as exc:
        logger.warning("database_auto_migrate_skipped", error=str(exc))

    ptb_app = create_application(settings)

    async with ptb_app:
        await ptb_app.start()
        await ptb_app.bot.delete_webhook(drop_pending_updates=False)
        await _set_command_menu(ptb_app)
        await ptb_app.updater.start_polling(
            drop_pending_updates=settings.webhook_drop_pending_updates,
            allowed_updates=_ALLOWED_UPDATES,
        )
        logger.info("nico_robin_started", mode="polling")
        _log_robin_banner("polling")

        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("nico_robin_interrupted")
            return
        finally:
            await ptb_app.updater.stop()
            await ptb_app.stop()
            await dispose_engine()
            logger.info("nico_robin_stopped")


def main() -> None:
    configure_logging(level=settings.log_level)
    _acquire_single_instance_lock()

    try:
        if settings.is_webhook_mode:
            asyncio.run(_webhook_mode())
        else:
            asyncio.run(_polling_mode())
    except KeyboardInterrupt:
        logger.info("nico_robin_shutdown_requested")


if __name__ == "__main__":
    main()
