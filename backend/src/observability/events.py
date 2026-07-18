"""Structured event helpers for domain logging."""

from __future__ import annotations

import logging
from typing import Any

from src.observability.context import get_request_id, get_user_id

# logging.LogRecord reserves these attribute names; remap if callers pass them.
_RESERVED_EXTRA_KEYS = {
    "name": "field_name",
    "msg": "field_msg",
    "args": "field_args",
    "created": "field_created",
    "filename": "file_name",
    "funcName": "field_func_name",
    "levelname": "field_level_name",
    "levelno": "field_level_no",
    "lineno": "field_lineno",
    "module": "field_module",
    "msecs": "field_msecs",
    "pathname": "field_pathname",
    "process": "field_process",
    "processName": "field_process_name",
    "relativeCreated": "field_relative_created",
    "stack_info": "field_stack_info",
    "exc_info": "field_exc_info",
    "exc_text": "field_exc_text",
    "thread": "field_thread",
    "threadName": "field_thread_name",
    "taskName": "field_task_name",
    "message": "field_message",
}


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
    # Drop Nones for cleaner JSON; rename keys that collide with LogRecord.
    safe: dict[str, Any] = {}
    for key, value in extra.items():
        if value is None:
            continue
        safe[_RESERVED_EXTRA_KEYS.get(key, key)] = value
    logger.log(level, message or event, extra=safe)
