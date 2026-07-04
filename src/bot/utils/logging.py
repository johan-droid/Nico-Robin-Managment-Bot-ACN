from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

SECRET_PATTERNS = [
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b"),  # Telegram bot tokens
    re.compile(r"\b(?:postgres(?:ql)?://|redis://)[^\s]+", re.IGNORECASE),  # DB URLs
    re.compile(r"\b(?:sk|rk|pk)_[A-Za-z0-9_-]+\b"),  # API keys
    re.compile(r"\b(?:password|passwd|pwd)=[^\s&]+", re.IGNORECASE),  # Passwords in URLs
    re.compile(r"\b(?:token|secret|key)=[^\s&]+", re.IGNORECASE),  # Tokens in URLs
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),  # UUIDs
    re.compile(r"\b(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b"),  # AWS keys
]
SECRET_KEYS = {
    "bot_token", "webhook_secret", "metrics_api_key", "data_encryption_key",
    "database_url", "redis_url", "celery_broker_url", "celery_result_backend",
    "password", "passwd", "pwd", "secret", "token", "key", "api_key",
    "access_token", "refresh_token", "client_secret", "private_key"
}


def _mask_secret_text(value: str) -> str:
    if not value or len(value) > 10000:  # Skip very large values
        return value

    masked = value
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub("[redacted]", masked)

    # Additional masking for common sensitive patterns
    masked = re.sub(r"\b[0-9]{16}\b", "[redacted]", masked)  # Credit card numbers
    masked = re.sub(r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", "[redacted]", masked)  # SSN pattern

    return masked


def _mask_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in SECRET_KEYS and isinstance(item, str):
                result[key] = "[redacted]"
            else:
                result[key] = _mask_sensitive_data(item)
        return result
    if isinstance(value, list):
        return [_mask_sensitive_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask_sensitive_data(item) for item in value)
    if isinstance(value, str):
        return _mask_secret_text(value)
    return value


def _mask_event_dict(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    del logger, method_name
    return _mask_sensitive_data(event_dict)


class SecretMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _mask_secret_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = _mask_sensitive_data(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(_mask_sensitive_data(arg) for arg in record.args)
        return True


def _resolve_logs_dir() -> Path | None:
    """Return a writable logs directory, or None if file logging is unavailable."""
    candidates: list[Path] = []
    env_logs_dir = os.getenv("LOG_DIR")
    if env_logs_dir:
        candidates.append(Path(env_logs_dir))
    candidates.append(Path("logs"))
    candidates.append(Path("/tmp/nico-robin-logs"))

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue
    return None


def _ensure_utf8_stream(stream: Any) -> Any:
    """Use UTF-8 for console streams when the platform supports it."""
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass
    return stream


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging with detailed context and file output."""
    logs_dir = _resolve_logs_dir()

    # Timestamper for ISO format
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
            _mask_event_dict,
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
    console_stream = _ensure_utf8_stream(sys.stdout)
    console_handler = logging.StreamHandler(console_stream)
    console_handler.setLevel(log_level)
    console_handler.addFilter(SecretMaskingFilter())
    console_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    file_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] [%(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    if logs_dir is not None:
        # File handler for all logs
        log_file = logs_dir / f"bot-{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # File gets everything
        file_handler.addFilter(SecretMaskingFilter())
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error log file
        error_file = logs_dir / f"errors-{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.addFilter(SecretMaskingFilter())
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

    # Keep third-party libraries quiet in the console; the file log still captures DEBUG.
    noisy_loggers = [
        "httpcore",
        "httpx",
        "telegram",
        "telegram.ext",
        "celery",
        "billiard",
        "asyncio",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Preserve useful debug output from the app and database layer when requested.
    if level == "DEBUG":
        for logger_name in ["src.bot", "sqlalchemy.engine", "uvicorn"]:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)

    logger = structlog.get_logger(__name__)
    logger.info(
        "logging_configured",
        level=level,
        logs_dir=str(logs_dir) if logs_dir is not None else None,
        file_logging_enabled=logs_dir is not None,
    )


def setup_logging(level: str = "INFO") -> None:
    """Backward-compatible alias for older imports."""
    configure_logging(level=level)


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
