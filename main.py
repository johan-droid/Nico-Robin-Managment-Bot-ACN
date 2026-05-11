from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import structlog
import uvicorn
from telegram import BotCommand

from bot.app import create_application
from client.websocket_client import (
    initialize_websocket_client,
    shutdown_websocket_client,
)
from config import settings
from database import dispose_engine, engine
from gateway.webhook import create_combined_app
from utils.logging import configure_logging

logger = structlog.get_logger(__name__)

_BOT_LOCK_HANDLE = None

_BOT_COMMANDS = [
    BotCommand("start", "DM welcome and bot intro"),
    BotCommand("help", "Show the main help message"),
    BotCommand("management", "Show management command guide"),
    BotCommand("ping", "Check if the bot is alive"),
    BotCommand("robin", "Get a Nico Robin quote"),
    BotCommand("features", "Show feature status"),
    BotCommand("my_features", "Show features for your role"),
    BotCommand("feature_info", "Show one feature's details"),
    BotCommand("feature_logs", "Show feature toggle history"),
    BotCommand("feature_stats", "Show feature usage stats"),
    BotCommand("enable", "Enable a feature"),
    BotCommand("disable", "Disable a feature"),
    BotCommand("toggle", "Toggle a feature"),
    BotCommand("enable_category", "Enable a feature category"),
    BotCommand("disable_category", "Disable a feature category"),
    BotCommand("reset_features", "Reset feature settings"),
    BotCommand("ban", "Ban a user"),
    BotCommand("unban", "Unban a user"),
    BotCommand("kick", "Kick a user"),
    BotCommand("mute", "Mute a user"),
    BotCommand("unmute", "Unmute a user"),
    BotCommand("warn", "Warn a user"),
    BotCommand("warns", "Show warning count"),
    BotCommand("resetwarn", "Reset warnings"),
    BotCommand("slowmode", "Set slow mode"),
    BotCommand("toggleai", "Toggle AI moderation"),
    BotCommand("del", "Delete a replied message"),
    BotCommand("purge", "Delete multiple messages"),
    BotCommand("pin", "Pin a message"),
    BotCommand("filter", "Add a word filter"),
    BotCommand("stop", "Remove a word filter"),
    BotCommand("filters", "List word filters"),
    BotCommand("filteraction", "Set filter action"),
    BotCommand("setwelcome", "Set welcome text"),
    BotCommand("resetwelcome", "Reset welcome text"),
    BotCommand("welcome", "Toggle welcome messages"),
    BotCommand("setfarewell", "Set goodbye text"),
    BotCommand("farewell", "Toggle goodbye messages"),
    BotCommand("cleanwelcome", "Toggle welcome cleanup"),
    BotCommand("welcometest", "Preview welcome message"),
    BotCommand("setrules", "Set group rules"),
    BotCommand("rules", "Show group rules"),
    BotCommand("stats", "Show group statistics"),
    BotCommand("id", "Show user or chat ID"),
    BotCommand("whois", "Inspect a user"),
    BotCommand("info", "Inspect a user"),
    BotCommand("save", "Save a note"),
    BotCommand("get", "Retrieve a note"),
    BotCommand("notes", "List notes"),
    BotCommand("clear", "Delete a note"),
    BotCommand("setlocale", "Change group language"),
    BotCommand("setwarnlimit", "Set warning limit"),
    BotCommand("setwarnaction", "Set warning action"),
    BotCommand("setflood", "Set flood limit"),
    BotCommand("setfloodmode", "Set flood punishment"),
    BotCommand("flood", "Show flood settings"),
    BotCommand("captcha", "Toggle CAPTCHA"),
    BotCommand("newfed", "Create a federation"),
    BotCommand("joinfed", "Join a federation"),
    BotCommand("schedule", "Schedule an announcement"),
    BotCommand("acn_status", "Show ACN status"),
    BotCommand("loyalty_leaderboard", "Show ACN leaderboard"),
    BotCommand("acn_members", "List ACN members"),
    BotCommand("acn_info", "Show ACN group info"),
    BotCommand("addacn", "Add an ACN member"),
    BotCommand("removeacn", "Remove an ACN member"),
    BotCommand("award", "Award loyalty points"),
    BotCommand("addacngroup", "Add group to ACN"),
    BotCommand("flirt", "Flirt with Nico Robin"),
    BotCommand("flirt_stats", "Show flirting stats"),
    BotCommand("flirt_categories", "Show flirt categories"),
    BotCommand("flirt_achievements", "Show flirt achievements"),
    BotCommand("flirt_example", "Show flirt examples"),
    BotCommand("bond_with_yamato", "Bond with Yamato"),
    BotCommand("yamato_status", "Show friendship status"),
    BotCommand("yamato_memories", "Show shared memories"),
    BotCommand("gift_to_yamato", "Send a gift to Yamato"),
    BotCommand("yamato_activities", "Show friendship activity"),
    BotCommand("yamato_help", "Show friendship help"),
    BotCommand("points", "Show your points"),
    BotCommand("leaderboard", "Show the points leaderboard"),
    BotCommand("apploids", "Show your apploids"),
    BotCommand("buy_apploid", "Buy an apploid"),
    BotCommand("equip_apploid", "Equip an apploid"),
    BotCommand("point_stats", "Show point stats"),
    BotCommand("earn_points", "Show point earning help"),
    BotCommand("point_help", "Show point system help"),
    BotCommand("profile", "Show a member profile"),
    BotCommand("setbio", "Set your profile bio"),
    BotCommand("addswear", "Add a swear word"),
    BotCommand("delswear", "Remove a swear word"),
    BotCommand("swearlist", "List swear words"),
    BotCommand("swearsettings", "View swear word settings"),
    BotCommand("broadcastchannels", "List broadcast channels"),
    BotCommand("broadcaststatus", "Show broadcast status"),
    BotCommand("testbroadcast", "Test a broadcast"),
    BotCommand("broadcasthelp", "Show broadcast help"),
    BotCommand("addbroadcast", "Add a broadcast channel"),
    BotCommand("removebroadcast", "Remove a broadcast channel"),
    BotCommand("addmaingroup", "Add a main ACN group"),
    BotCommand("channelpost", "Send to a channel"),
    BotCommand("channelphoto", "Send photo to a channel"),
    BotCommand("addpurgechannel", "Add an auto-purge channel"),
    BotCommand("removepurgechannel", "Remove an auto-purge channel"),
    BotCommand("purgechannels", "List purge channels"),
]


def _log_robin_banner(mode: str) -> None:
    """Emit a small Robin-style ready banner in the logs."""
    banner_lines = [
        r"  /\_/\\",
        r" ( •.• )  Nico Robin Bot",
        r" / >🌸< \  backend ready",
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
            lock_handle.write(b"0")
            lock_handle.flush()
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception as e:
        lock_handle.close()
        logger.error("bot_already_running", lock_file=str(lock_path))
        raise SystemExit(1) from e

    _BOT_LOCK_HANDLE = lock_handle


async def _set_command_menu(application) -> None:
    """Register the hardcoded slash-command menu with Telegram."""
    await application.bot.set_my_commands(_BOT_COMMANDS)
    logger.info("bot_command_menu_configured", command_count=len(_BOT_COMMANDS))


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
            logger.warning(
                "database_connection_failed", retries_left=retries, error=str(e)
            )
            if retries == 0:
                logger.error("database_connection_exhausted")
                sys.exit(1)
            await asyncio.sleep(2.0)


async def _auto_migrate() -> None:
    """Run Alembic migrations automatically on startup."""
    try:
        import asyncio

        from alembic.config import Config as AlembicConfig

        from alembic import command as alembic_cmd

        def run_upgrade():
            cfg = AlembicConfig("alembic.ini")
            alembic_cmd.upgrade(cfg, "head")

        # Run the sync Alembic commands in a threadpool to avoid blocking the event loop
        await asyncio.to_thread(run_upgrade)
        logger.info("database_migrated_successfully")
    except Exception as exc:
        logger.error("database_migration_failed", error=str(exc))
        raise


async def _webhook_mode() -> None:
    """Run bot in webhook mode with ASGI server."""
    logger.info("bot_mode", mode="webhook", webhook_url=settings.webhook_url)

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

        if settings.webhook_url and settings.webhook_url.startswith("https://"):
            webhook_url = settings.webhook_url
            if not webhook_url.endswith("/webhook"):
                webhook_url = f"{webhook_url.rstrip('/')}/webhook"

            await ptb_app.bot.set_webhook(
                url=webhook_url,
                secret_token=settings.webhook_secret or None,
                drop_pending_updates=True,
            )
            logger.info("telegram_webhook_configured", url=webhook_url)

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
        await _set_command_menu(ptb_app)
        await ptb_app.updater.start_polling(
            allowed_updates=None,
            drop_pending_updates=True,
        )
        logger.info("nico_robin_started", mode="polling")
        _log_robin_banner("polling")

        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("nico_robin_interrupted")
            raise
        finally:
            await ptb_app.updater.stop()
            await ptb_app.stop()
            await dispose_engine()
            logger.info("nico_robin_stopped")


if __name__ == "__main__":
    configure_logging(level=settings.log_level)
    _acquire_single_instance_lock()

    # Polling mode uses blocking run_polling(), webhook mode is async
    if not settings.webhook_url or not settings.webhook_url.startswith("https://"):
        asyncio.run(_polling_mode())
    else:
        asyncio.run(_webhook_mode())
