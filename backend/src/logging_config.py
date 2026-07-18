"""Production-grade structured logging setup."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from src.config import get_settings
from src.observability.formatter import JsonFormatter, TextFormatter

_CONFIGURED = False


def setup_logging(*, force: bool = False) -> logging.Logger:
    """Configure app logger once (JSON or text via LOG_FORMAT)."""
    global _CONFIGURED
    settings = get_settings()
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    logger = logging.getLogger("legal_rag")
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    logger.setLevel(level)

    if _CONFIGURED and logger.handlers and not force:
        return logger

    # Replace any prior handlers (e.g. test reloads)
    logger.handlers.clear()

    use_json = settings.LOG_FORMAT == "json"
    formatter: logging.Formatter = JsonFormatter() if use_json else TextFormatter()

    if settings.LOG_TO_CONSOLE:
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(formatter)
        logger.addHandler(console)

    if settings.LOG_TO_FILE:
        file_handler = RotatingFileHandler(
            os.path.join(settings.LOG_DIR, settings.LOG_FILE_NAME),
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    _CONFIGURED = True
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return app logger (optionally a child logger)."""
    base = setup_logging()
    if not name or name == "legal_rag":
        return base
    return base.getChild(name)


# Default module-level logger used across the app
logger = setup_logging()
