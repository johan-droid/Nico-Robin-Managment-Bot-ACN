from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging with detailed context and file output."""

    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Timestamper for ISO format
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (
                structlog.dev.ConsoleRenderer()
                if level == "DEBUG"
                else structlog.processors.JSONRenderer()
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Create formatters
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Console handler with detailed format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    # File handler for all logs
    log_file = logs_dir / f"bot-{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # File gets everything
    file_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] [%(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Error log file
    error_file = logs_dir / f"errors-{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_file, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Set specific loggers to DEBUG for detailed info
    debug_loggers = [
        "telegram.ext",
        "sqlalchemy.engine",
        "uvicorn",
        "asyncio",
    ]
    for logger_name in debug_loggers:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)

    logger = structlog.get_logger(__name__)
    logger.info("logging_configured", level=level, logs_dir=str(logs_dir))


def bind_update_context(
    update_id: int | None = None,
    user_id: int | None = None,
    chat_id: int | None = None,
    **values: Any,
) -> None:
    """Bind detailed context to all logs in current scope."""
    context = {"update_id": update_id, "user_id": user_id, "chat_id": chat_id, **values}
    # Remove None values
    context = {k: v for k, v in context.items() if v is not None}
    structlog.contextvars.bind_contextvars(**context)


def clear_update_context() -> None:
    """Clear all bound context from logs."""
    structlog.contextvars.clear_contextvars()
