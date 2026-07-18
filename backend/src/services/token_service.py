"""Auth token helpers for email verify / password reset."""

import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.models import AuthToken, User

settings = get_settings()


def create_token(db: Session, user: User, purpose: str) -> AuthToken:
    token = secrets.token_urlsafe(32)
    row = AuthToken(
        user_id=user.id,
        token=token,
        purpose=purpose,
        expires_at=datetime.utcnow()
        + timedelta(hours=settings.TOKEN_EXPIRE_HOURS),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def consume_token(db: Session, token: str, purpose: str) -> User | None:
    row = (
        db.query(AuthToken)
        .filter(
            AuthToken.token == token,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
        .first()
    )
    if not row:
        return None
    if row.expires_at < datetime.utcnow():
        return None
    row.used_at = datetime.utcnow()
    user = db.get(User, row.user_id)
    db.commit()
    return user
