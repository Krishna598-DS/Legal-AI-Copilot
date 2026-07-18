"""FastAPI exception handlers — standardized JSON, no internal leaks."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.errors.exceptions import AppError, DatabaseError, InternalError, OpenAIServiceError
from src.logging_config import logger
from src.observability.events import log_event


def error_body(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


def _json(status_code: int, payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload)


def _http_exception_payload(exc: StarletteHTTPException) -> tuple[str, str, dict]:
    """Normalize legacy HTTPException.detail into code/message/details."""
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        message = str(detail.get("message") or detail.get("detail") or "Request failed.")
        details = {
            k: v
            for k, v in detail.items()
            if k not in {"code", "message", "detail"}
        }
        return code, message, details
    if isinstance(detail, list):
        return (
            "VALIDATION_ERROR",
            "Validation failed.",
            {"errors": detail},
        )
    text = str(detail) if detail is not None else "Request failed."
    # Map common auth status codes
    if exc.status_code == 401:
        return "AUTHENTICATION_REQUIRED", text, {}
    if exc.status_code == 403:
        return "FORBIDDEN", text, {}
    if exc.status_code == 404:
        return "NOT_FOUND", text, {}
    if exc.status_code == 429:
        return "RATE_LIMIT_EXCEEDED", text, {}
    return "HTTP_ERROR", text, {}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all centralized handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            log_event(
                logger,
                "error",
                level=logging.ERROR,
                message=exc.message,
                error_code=exc.code,
                endpoint=request.url.path,
                method=request.method,
            )
        return _json(exc.status_code, exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Safe field paths only — no internal frames
        errors = []
        for err in exc.errors():
            errors.append(
                {
                    "loc": list(err.get("loc", ())),
                    "msg": err.get("msg", "Invalid value"),
                    "type": err.get("type", "value_error"),
                }
            )
        return _json(
            422,
            error_body(
                "VALIDATION_ERROR",
                "Request validation failed.",
                {"errors": errors},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code, message, details = _http_exception_payload(exc)
        headers = getattr(exc, "headers", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, message, details),
            headers=headers,
        )

    try:
        from sqlalchemy.exc import SQLAlchemyError
    except ImportError:  # pragma: no cover
        SQLAlchemyError = None  # type: ignore[misc, assignment]

    if SQLAlchemyError is not None:

        @app.exception_handler(SQLAlchemyError)
        async def sqlalchemy_handler(
            request: Request, exc: SQLAlchemyError
        ) -> JSONResponse:
            log_event(
                logger,
                "error",
                level=logging.ERROR,
                message="database error",
                error_type=type(exc).__name__,
                endpoint=request.url.path,
                method=request.method,
            )
            logger.exception("Database error on %s %s", request.method, request.url.path)
            err = DatabaseError()
            return _json(err.status_code, err.to_dict())

    try:
        from openai import APIError as OpenAIAPIError
    except ImportError:  # pragma: no cover
        OpenAIAPIError = None  # type: ignore[misc, assignment]

    if OpenAIAPIError is not None:

        @app.exception_handler(OpenAIAPIError)
        async def openai_handler(
            request: Request, exc: OpenAIAPIError
        ) -> JSONResponse:
            log_event(
                logger,
                "error",
                level=logging.ERROR,
                message="openai api error",
                error_type=type(exc).__name__,
                endpoint=request.url.path,
                method=request.method,
            )
            err = OpenAIServiceError(details={"type": type(exc).__name__})
            return _json(err.status_code, err.to_dict())

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="unhandled exception",
            error_type=type(exc).__name__,
            endpoint=request.url.path,
            method=request.method,
        )
        logger.exception(
            "Unhandled error on %s %s", request.method, request.url.path
        )
        err = InternalError()
        return _json(err.status_code, err.to_dict())
