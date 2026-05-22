from __future__ import annotations

import logging
import os
import sys
import threading
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog


def _log_fatal_exception(exc_type, exc_value, exc_traceback) -> None:
    logging.getLogger(__name__).critical(
        "unhandled_fatal_exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging with detailed context and file output."""

    # Prefer a local logs directory, but fall back to a writable temp path on
    # read-only deploy filesystems such as Render.
    logs_dir = Path(os.environ.get("NICO_ROBIN_LOG_DIR", "logs"))
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logs_dir = Path(tempfile.gettempdir()) / "nico_robin_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

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

    file_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] [%(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handlers: list[logging.Handler] = []
    try:
        # File handler for all logs
        log_file = logs_dir / f"bot-{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # File gets everything
        file_handler.setFormatter(file_formatter)
        file_handlers.append(file_handler)

        # Error log file
        error_file = logs_dir / f"errors-{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        file_handlers.append(error_handler)
    except OSError:
        # Keep startup alive even if the filesystem refuses file logging.
        file_handlers = []

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)
    root_logger.addHandler(console_handler)
    for handler in file_handlers:
        root_logger.addHandler(handler)

    sys.excepthook = _log_fatal_exception
    threading.excepthook = lambda args: _log_fatal_exception(  # type: ignore[assignment]
        args.exc_type,
        args.exc_value,
        args.exc_traceback,
    )

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


def configure_logging(level: str = "INFO") -> None:
    """Backward-compatible alias for setup_logging."""

    setup_logging(level=level)


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
