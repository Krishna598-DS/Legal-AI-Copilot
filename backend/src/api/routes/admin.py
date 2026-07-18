"""Admin routes — restricted to ADMIN_EMAILS."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.auth.schemas import (
    ProfessionalCreateRequest,
    ProfessionalResponse,
    ProfessionalUpdateRequest,
)
from src.config import get_settings
from src.db.database import get_db
from src.db.models import ChatMessage, Document, LegalProfessional, UsageEvent, User
from src.directory import get_directory_provider
from src.errors import AuthorizationError, NotFoundError, ValidationAppError
from src.llm.expert_prompts import EXPERT_CATEGORIES

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    # Read settings at request time so tests/env changes are honored.
    settings = get_settings()
    allowed = {
        e.strip().lower()
        for e in settings.ADMIN_EMAILS.split(",")
        if e.strip()
    }
    if not allowed or user.email.lower() not in allowed:
        raise AuthorizationError(
            "Admin access required.",
            code="ADMIN_REQUIRED",
        )
    return user


@router.get("/stats")
def stats(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {
        "users": db.query(func.count(User.id)).scalar() or 0,
        "documents": db.query(func.count(Document.id)).scalar() or 0,
        "messages": db.query(func.count(ChatMessage.id)).scalar() or 0,
        "usage_events": db.query(func.count(UsageEvent.id)).scalar() or 0,
        "professionals": db.query(func.count(LegalProfessional.id)).scalar() or 0,
        "version": settings.APP_VERSION,
        "directory_provider": settings.DIRECTORY_PROVIDER,
    }


@router.get("/users")
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).limit(200).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": getattr(u, "role", None) or "individual",
            "plan": u.plan,
            "email_verified": u.email_verified,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "document_count": db.query(Document)
            .filter(Document.user_id == u.id)
            .count(),
        }
        for u in users
    ]


@router.post("/users/{user_id}/disable")
def disable_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise ValidationAppError(
            "Cannot disable yourself.",
            code="CANNOT_DISABLE_SELF",
        )
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found.", code="USER_NOT_FOUND")
    user.is_active = False
    db.commit()
    return {"message": "User disabled", "id": user_id}


@router.post("/users/{user_id}/enable")
def enable_user(
    user_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found.", code="USER_NOT_FOUND")
    user.is_active = True
    db.commit()
    return {"message": "User enabled", "id": user_id}


@router.get("/professionals", response_model=list[ProfessionalResponse])
def admin_list_professionals(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all directory professionals (including unverified)."""
    provider = get_directory_provider(db)
    rows = provider.list_professionals(verified_only=False, limit=500, offset=0)
    return [ProfessionalResponse(**r) for r in rows]


@router.get("/professionals/categories")
def admin_professional_categories(_: User = Depends(require_admin)):
    """Suggested specialization values aligned with expert recommendation."""
    return {"categories": list(EXPERT_CATEGORIES)}


@router.post("/professionals", response_model=ProfessionalResponse)
def admin_create_professional(
    payload: ProfessionalCreateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually add a legal professional to the local directory."""
    provider = get_directory_provider(db)
    row = provider.create_professional(payload.model_dump())
    return ProfessionalResponse(**row)


@router.patch("/professionals/{professional_id}", response_model=ProfessionalResponse)
def admin_update_professional(
    professional_id: str,
    payload: ProfessionalUpdateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    provider = get_directory_provider(db)
    data = payload.model_dump(exclude_unset=True)
    row = provider.update_professional(professional_id, data)
    if not row:
        raise NotFoundError(
            "Professional not found.",
            code="PROFESSIONAL_NOT_FOUND",
        )
    return ProfessionalResponse(**row)


@router.delete("/professionals/{professional_id}")
def admin_delete_professional(
    professional_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    provider = get_directory_provider(db)
    deleted = provider.delete_professional(professional_id)
    if not deleted:
        raise NotFoundError(
            "Professional not found.",
            code="PROFESSIONAL_NOT_FOUND",
        )
    return {"message": "Professional deleted", "id": professional_id}
