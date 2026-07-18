"""Observability: structured logging helpers and request middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.observability.events import log_event
    from src.observability.middleware import RequestLoggingMiddleware

__all__ = ["RequestLoggingMiddleware", "log_event"]


def __getattr__(name: str):
    if name == "log_event":
        from src.observability.events import log_event

        return log_event
    if name == "RequestLoggingMiddleware":
        from src.observability.middleware import RequestLoggingMiddleware

        return RequestLoggingMiddleware
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
