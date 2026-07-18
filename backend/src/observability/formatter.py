"""JSON and plain-text log formatters."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from src.observability.context import get_request_id, get_user_id


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None) or get_request_id()
        user_id = getattr(record, "user_id", None) or get_user_id()
        if request_id:
            payload["request_id"] = request_id
        if user_id:
            payload["user_id"] = user_id

        # Structured extras (skip std LogRecord internals)
        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
            "request_id",
            "user_id",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key in reserved or key.startswith("_") or value is None:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Human-readable fallback for local debugging."""

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id and "request_id=" not in record.getMessage():
            record.msg = f"[request_id={request_id}] {record.msg}"
        return super().format(record)
