"""Auth routes: register, login, verify, reset, Google SSO stub."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import enforce_auth_rate_limit, get_current_user
from src.auth.schemas import (
    GoogleAuthRequest,
    GoogleConfigResponse,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.auth.personas import (
    DEFAULT_ROLE,
    normalize_role,
    role_label,
    welcome_message,
)
from src.auth.security import create_access_token, hash_password, verify_password
from src.config import get_settings
from src.db.database import get_db
from src.db.models import Document, User
from src.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ServiceUnavailableError,
    ValidationAppError,
)
from src.logging_config import logger
from src.observability.context import set_user_id
from src.observability.events import log_event
from src.services import email_service, token_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

DISCLAIMER_REQUIRED = (
    "You must accept the legal disclaimer to create an account. "
    "This product is not a law firm and does not provide legal advice."
)


def _user_response(user: User, db: Session) -> UserResponse:
    count = db.query(Document).filter(Document.user_id == user.id).count()
    role = normalize_role(getattr(user, "role", None))
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role,
        role_label=role_label(role),
        welcome_message=welcome_message(role),
        created_at=user.created_at,
        accepted_disclaimer_at=user.accepted_disclaimer_at,
        email_verified=bool(user.email_verified),
        terms_version=user.terms_version,
        privacy_version=user.privacy_version,
        plan=user.plan or "free",
        org_id=user.org_id,
        org_role=user.org_role,
        document_count=count,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_auth_rate_limit),
):
    if not payload.accept_disclaimer:
        raise ValidationAppError(
            DISCLAIMER_REQUIRED,
            code="DISCLAIMER_REQUIRED",
        )

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise ConflictError(
            "Email already registered.",
            code="EMAIL_ALREADY_REGISTERED",
        )

    verified = not settings.REQUIRE_EMAIL_VERIFICATION
    persona = normalize_role(payload.role)
    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=persona,
        accepted_disclaimer_at=datetime.utcnow(),
        terms_version=settings.TERMS_VERSION,
        privacy_version=settings.PRIVACY_VERSION,
        email_verified=verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token_row = token_service.create_token(db, user, "verify_email")
    email_service.send_verification_email(user.email, token_row.token)
    set_user_id(user.id)
    log_event(
        logger,
        "register",
        message="user registered",
        user_id=user.id,
        email=user.email,
        role=persona,
    )

    return TokenResponse(
        access_token=create_access_token(user.id),
        email_verified=user.email_verified,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_auth_rate_limit),
):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if (
        not user
        or not user.hashed_password
        or not verify_password(payload.password, user.hashed_password)
    ):
        log_event(
            logger,
            "login_failed",
            level=logging.WARNING,
            message="login failed",
            email=payload.email.lower(),
        )
        raise AuthenticationError(
            "Incorrect email or password.",
            code="INVALID_CREDENTIALS",
        )
    if not user.is_active:
        raise AuthorizationError(
            "Account is disabled.",
            code="ACCOUNT_DISABLED",
        )

    set_user_id(user.id)
    log_event(
        logger,
        "login",
        message="user logged in",
        user_id=user.id,
        email=user.email,
    )
    return TokenResponse(
        access_token=create_access_token(user.id),
        email_verified=bool(user.email_verified),
    )


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    """Stateless JWT logout marker — client should discard the token."""
    log_event(
        logger,
        "logout",
        message="user logged out",
        user_id=user.id,
        email=user.email,
    )
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _user_response(user, db)


@router.get("/verify-email")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    user = token_service.consume_token(db, token, "verify_email")
    if not user:
        raise ValidationAppError(
            "Invalid or expired token.",
            code="INVALID_TOKEN",
        )
    user.email_verified = True
    db.commit()
    return {"message": "Email verified successfully", "email": user.email}


@router.post("/resend-verification")
def resend_verification(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.email_verified:
        return {"message": "Email already verified"}
    token_row = token_service.create_token(db, user, "verify_email")
    email_service.send_verification_email(user.email, token_row.token)
    return {"message": "Verification email sent"}


@router.post("/forgot-password")
def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user and user.hashed_password:
        token_row = token_service.create_token(db, user, "reset_password")
        email_service.send_password_reset_email(user.email, token_row.token)
    return {"message": "If that email exists, a reset link was sent"}


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    user = token_service.consume_token(db, payload.token, "reset_password")
    if not user:
        raise ValidationAppError(
            "Invalid or expired token.",
            code="INVALID_TOKEN",
        )
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated"}


@router.get("/google/config", response_model=GoogleConfigResponse)
def google_config():
    """Public client config for Sign in with Google (client_id is not a secret)."""
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    return GoogleConfigResponse(enabled=bool(client_id), client_id=client_id or None)


@router.post("/google", response_model=TokenResponse)
def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Google SSO entrypoint.
    Requires GOOGLE_CLIENT_ID. Verifies ID token via google-auth when installed.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise ServiceUnavailableError(
            "Google SSO not configured.",
            code="GOOGLE_SSO_UNAVAILABLE",
        )
    try:
        from google.auth.transport import requests as greq
        from google.oauth2 import id_token
    except ImportError as exc:
        raise ServiceUnavailableError(
            "Google SSO is not available on this server.",
            code="GOOGLE_SSO_UNAVAILABLE",
        ) from exc

    try:
        info = id_token.verify_oauth2_token(
            payload.id_token,
            greq.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise AuthenticationError(
            "Invalid Google token.",
            code="INVALID_GOOGLE_TOKEN",
        ) from exc

    email = (info.get("email") or "").lower()
    sub = info.get("sub")
    if not email or not sub:
        raise ValidationAppError(
            "Google token missing email.",
            code="GOOGLE_TOKEN_INVALID",
        )

    user = (
        db.query(User).filter((User.google_sub == sub) | (User.email == email)).first()
    )
    if not user:
        if not payload.accept_disclaimer:
            raise ValidationAppError(
                DISCLAIMER_REQUIRED,
                code="DISCLAIMER_REQUIRED",
            )
        user = User(
            email=email,
            full_name=info.get("name"),
            google_sub=sub,
            email_verified=True,
            hashed_password=None,
            role=normalize_role(payload.role) if payload.role else DEFAULT_ROLE,
            accepted_disclaimer_at=datetime.utcnow(),
            terms_version=settings.TERMS_VERSION,
            privacy_version=settings.PRIVACY_VERSION,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.google_sub = sub
        user.email_verified = True
        db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        email_verified=True,
    )
