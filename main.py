from __future__ import annotations

import asyncio

import structlog
import uvicorn

from bot.app import create_application
from client.websocket_client import (
    initialize_websocket_client,
    shutdown_websocket_client,
)
from config import settings
from database import engine
from gateway.webhook import create_combined_app
from models import Base
from utils.logging import configure_logging

logger = structlog.get_logger(__name__)


async def _auto_migrate() -> None:
    """Auto-create database tables on startup.

    Uses checkfirst=True so existing tables are never overwritten.
    New models added to models/__init__.py are auto-detected.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    logger.info("database_auto_migrated", tables=len(Base.metadata.tables))

    # Stamp alembic to head so manual migrations stay in sync
    try:
        from alembic.config import Config as AlembicConfig

        from alembic import command as alembic_cmd

        cfg = AlembicConfig("alembic.ini")
        alembic_cmd.stamp(cfg, "head")
        logger.info("alembic_stamped_head")
    except Exception:
        pass  # Alembic not configured is fine


async def main() -> None:
    configure_logging()

    # Auto-migrate database before starting bot
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
    )
    server = uvicorn.Server(server_config)

    async with ptb_app:
        # Start the bot application first so `bot.get_me()` works
        await ptb_app.start()

        # Serve the ASGI app in a background task so the server is accepting
        # connections before the WebSocket client attempts to connect.
        server_task = asyncio.create_task(server.serve())

        # Give the server time to bind the port and initialize Socket.IO endpoints
        # In containerized environments, this may take longer due to startup delays
        await asyncio.sleep(2.0)

        # Initialize WebSocket client (will connect to the running server)
        await initialize_websocket_client(ptb_app)

        if settings.webhook_url and settings.webhook_url.startswith("https://"):
            webhook_url = f"{settings.webhook_url.rstrip('/')}/webhook"
            await ptb_app.bot.set_webhook(
                url=webhook_url,
                secret_token=settings.webhook_secret or None,
                drop_pending_updates=True,
            )
            logger.info("telegram_webhook_configured", url=webhook_url)
        elif settings.webhook_url:
            logger.info(
                "telegram_webhook_skipped",
                url=settings.webhook_url,
                reason="non_https_url",
            )

        logger.info("nico_robin_started", port=settings.port)

        if settings.websocket_enabled:
            logger.info("websocket_enabled", port=settings.websocket_port)

        try:
            await server_task
        finally:
            # Shutdown WebSocket client
            await shutdown_websocket_client()
            await ptb_app.stop()
            logger.info("nico_robin_stopped")


if __name__ == "__main__":
    asyncio.run(main())
