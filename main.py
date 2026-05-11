from __future__ import annotations

import asyncio
import sys

import structlog
import uvicorn

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


async def _wait_for_db() -> None:
    """Wait for the database to be ready before starting."""
    retries = 5
    import asyncio

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


async def main() -> None:
    configure_logging()

    # 1. Wait for database to be ready
    await _wait_for_db()

    # 2. Auto-migrate database
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
            webhook_url = settings.webhook_url
            if not webhook_url.endswith("/webhook"):
                webhook_url = f"{webhook_url.rstrip('/')}/webhook"
                
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
            await dispose_engine()
            logger.info("nico_robin_stopped")


if __name__ == "__main__":
    asyncio.run(main())
