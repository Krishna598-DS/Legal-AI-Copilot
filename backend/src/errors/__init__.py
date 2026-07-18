"""Centralized application errors and HTTP handlers."""

from src.errors.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    DocumentNotFoundError,
    NotFoundError,
    OpenAIServiceError,
    RateLimitExceededError,
    RetrievalError,
    ServiceUnavailableError,
    UploadError,
    ValidationAppError,
)
from src.errors.handlers import register_exception_handlers

__all__ = [
    "AppError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "DatabaseError",
    "DocumentNotFoundError",
    "NotFoundError",
    "OpenAIServiceError",
    "RateLimitExceededError",
    "RetrievalError",
    "ServiceUnavailableError",
    "UploadError",
    "ValidationAppError",
    "register_exception_handlers",
]
