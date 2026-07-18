"""Custom application exceptions (safe for client responses)."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """
    Base API error.

    Handlers serialize this to:
      {"error": {"code": "...", "message": "...", "details": {}}}
    """

    status_code: int = 400
    code: str = "APP_ERROR"
    message: str = "An error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message if message is not None else type(self).message
        self.code = code if code is not None else type(self).code
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        else:
            self.status_code = type(self).status_code
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"
    message = "Authentication required."


class AuthorizationError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found."


class DocumentNotFoundError(NotFoundError):
    code = "DOCUMENT_NOT_FOUND"
    message = "Document not found."


class ValidationAppError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "Validation failed."


class UploadError(AppError):
    status_code = 400
    code = "UPLOAD_ERROR"
    message = "Upload rejected."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "Conflict."


class RateLimitExceededError(AppError):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"
    message = "Rate limit exceeded."


class OpenAIServiceError(AppError):
    status_code = 502
    code = "OPENAI_ERROR"
    message = "The AI service is temporarily unavailable."


class RetrievalError(AppError):
    status_code = 502
    code = "RETRIEVAL_ERROR"
    message = "Document retrieval failed."


class DatabaseError(AppError):
    status_code = 503
    code = "DATABASE_ERROR"
    message = "A database error occurred. Please try again later."


class ServiceUnavailableError(AppError):
    status_code = 501
    code = "SERVICE_UNAVAILABLE"
    message = "This feature is not available."


class InternalError(AppError):
    status_code = 500
    code = "INTERNAL_ERROR"
    message = "An unexpected error occurred."
