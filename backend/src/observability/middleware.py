"""FastAPI/Starlette middleware: request_id + access logs."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.auth.security import decode_access_token
from src.logging_config import logger
from src.observability.context import (
    reset_request_id,
    reset_user_id,
    set_request_id,
    set_user_id,
)
from src.observability.events import log_event


def _extract_user_id(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    return decode_access_token(token)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Assign X-Request-ID and emit a structured http_request log line."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID") or request.headers.get(
            "X-Request-Id"
        )
        request_id = (incoming or uuid.uuid4().hex).strip()
        user_id = _extract_user_id(request)

        rid_token = set_request_id(request_id)
        uid_token = set_user_id(user_id)
        request.state.request_id = request_id
        if user_id:
            request.state.user_id = user_id

        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            import logging

            log_event(
                logger,
                "error",
                level=logging.ERROR,
                message="Unhandled exception during request",
                endpoint=request.url.path,
                method=request.method,
                status_code=status_code,
                latency_ms=latency_ms,
                user_id=user_id,
                request_id=request_id,
            )
            logger.exception(
                "unhandled_error",
                extra={
                    "event": "error",
                    "endpoint": request.url.path,
                    "method": request.method,
                    "request_id": request_id,
                    "user_id": user_id,
                },
            )
            raise
        finally:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            # Skip noisy static assets at DEBUG only
            path = request.url.path
            if path.startswith("/static"):
                logger.debug(
                    "static_request",
                    extra={
                        "event": "http_request",
                        "endpoint": path,
                        "method": request.method,
                        "status_code": status_code,
                        "latency_ms": latency_ms,
                        "request_id": request_id,
                        "user_id": user_id,
                    },
                )
            else:
                log_event(
                    logger,
                    "http_request",
                    message="request completed",
                    endpoint=path,
                    method=request.method,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    user_id=user_id,
                    request_id=request_id,
                )
            reset_user_id(uid_token)
            reset_request_id(rid_token)
