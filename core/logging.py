from __future__ import annotations

import logging
import os
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _fatal_exception(exc_type, exc_value, exc_traceback) -> None:
    logging.getLogger("nico_robin").critical(
        "unhandled_fatal_exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def setup_logging(level: str = "INFO", log_dir: str | None = None) -> None:
    logs_dir = Path(log_dir or os.getenv("NICO_ROBIN_LOG_DIR", "logs"))
    logs_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)

    log_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] [%(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    file_name = logs_dir / f"nico-robin-{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = RotatingFileHandler(file_name, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    error_name = logs_dir / f"nico-robin-errors-{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = RotatingFileHandler(error_name, maxBytes=10_000_000, backupCount=10, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    logging.captureWarnings(True)
    sys.excepthook = _fatal_exception
    threading.excepthook = lambda args: _fatal_exception(  # type: ignore[assignment]
        args.exc_type, args.exc_value, args.exc_traceback
    )
    logging.getLogger(__name__).info("logging_configured", extra={"level": level, "log_dir": str(logs_dir)})
