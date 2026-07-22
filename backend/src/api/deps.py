"""FastAPI dependencies: DB session, current user, rate limits."""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.auth.security import decode_access_token
from src.config import get_settings
from src.db.database import get_db
from src.db.models import Document, User
from src.errors import (
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
)
from src.services import rate_limit

security_scheme = HTTPBearer(auto_error=False)
settings = get_settings()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError(
            "Not authenticated.",
            code="AUTHENTICATION_REQUIRED",
        )

    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise AuthenticationError(
            "Invalid or expired token.",
            code="INVALID_TOKEN",
        )

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise AuthenticationError(
            "User not found or inactive.",
            code="USER_INACTIVE",
        )
    return user


def require_verified_user(user: User = Depends(get_current_user)) -> User:
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.email_verified:
        raise AuthorizationError(
            "Email not verified. Check your inbox or resend verification.",
            code="EMAIL_NOT_VERIFIED",
        )
    return user


def enforce_question_rate_limit(
    user: User = Depends(require_verified_user),
) -> User:
    allowed, _ = rate_limit.hit(
        f"question:{user.id}", settings.MAX_QUESTIONS_PER_HOUR
    )
    if not allowed:
        raise RateLimitExceededError(
            f"Rate limit exceeded: max {settings.MAX_QUESTIONS_PER_HOUR} "
            "questions per hour.",
            details={"limit": settings.MAX_QUESTIONS_PER_HOUR, "resource": "questions"},
        )
    return user


def enforce_upload_rate_limit(
    user: User = Depends(require_verified_user),
) -> User:
    allowed, _ = rate_limit.hit(
        f"upload:{user.id}", settings.MAX_UPLOADS_PER_HOUR
    )
    if not allowed:
        raise RateLimitExceededError(
            f"Rate limit exceeded: max {settings.MAX_UPLOADS_PER_HOUR} "
            "uploads per hour.",
            details={"limit": settings.MAX_UPLOADS_PER_HOUR, "resource": "uploads"},
        )
    return user


def enforce_auth_rate_limit(request: Request) -> None:
    """Deployment-readiness fix: login/register previously had no rate limiting at
    all, unlike every other user-facing endpoint. Keyed by client IP, since no
    authenticated user exists yet at the point of a login/register attempt."""
    client_ip = request.client.host if request.client else "unknown"
    allowed, _ = rate_limit.hit(
        f"auth:{client_ip}", settings.MAX_AUTH_ATTEMPTS_PER_HOUR
    )
    if not allowed:
        raise RateLimitExceededError(
            f"Too many login/registration attempts. Max "
            f"{settings.MAX_AUTH_ATTEMPTS_PER_HOUR} per hour — try again later.",
            details={"limit": settings.MAX_AUTH_ATTEMPTS_PER_HOUR, "resource": "auth"},
        )


def get_usage_counts(user_id: str, db: Session) -> dict:
    owned = db.query(Document).filter(Document.user_id == user_id).count()
    return {
        "questions_last_hour": rate_limit.current_count(f"question:{user_id}"),
        "uploads_last_hour": rate_limit.current_count(f"upload:{user_id}"),
        "questions_limit": settings.MAX_QUESTIONS_PER_HOUR,
        "uploads_limit": settings.MAX_UPLOADS_PER_HOUR,
        "documents_owned": owned,
        "documents_limit": settings.MAX_DOCUMENTS_PER_USER,
    }
