"""Structured event helpers for domain logging."""

from __future__ import annotations

import logging
from typing import Any

from src.observability.context import get_request_id, get_user_id


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    message: str | None = None,
    **fields: Any,
) -> None:
    """
    Log a named application event as structured fields.

    Example:
        log_event(logger, "login", user_id=user.id, email=user.email)
    """
    extra = {
        "event": event,
        "request_id": fields.pop("request_id", None) or get_request_id(),
        "user_id": fields.pop("user_id", None) or get_user_id(),
        **fields,
    }
    # Drop Nones for cleaner JSON
    extra = {k: v for k, v in extra.items() if v is not None}
    logger.log(level, message or event, extra=extra)
