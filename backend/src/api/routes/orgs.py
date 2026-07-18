"""Organization / team workspace routes."""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.auth.schemas import OrgCreateRequest, OrgInviteRequest
from src.db.database import get_db
from src.db.models import OrgInvite, Organization, User
from src.errors import AuthorizationError, ValidationAppError
from src.services import email_service

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.post("")
def create_org(
    payload: OrgCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.org_id:
        raise ValidationAppError(
            "Already in an organization.",
            code="ALREADY_IN_ORG",
        )
    org = Organization(name=payload.name)
    db.add(org)
    db.flush()
    user.org_id = org.id
    user.org_role = "admin"
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name, "role": "admin"}


@router.get("/me")
def my_org(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.org_id:
        return {"organization": None}
    org = db.get(Organization, user.org_id)
    members = (
        db.query(User)
        .filter(User.org_id == user.org_id)
        .all()
    )
    return {
        "organization": {"id": org.id, "name": org.name} if org else None,
        "role": user.org_role,
        "members": [
            {"id": m.id, "email": m.email, "role": m.org_role, "full_name": m.full_name}
            for m in members
        ],
    }


@router.post("/invite")
def invite_member(
    payload: OrgInviteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.org_id or user.org_role != "admin":
        raise AuthorizationError(
            "Admin role required.",
            code="ORG_ADMIN_REQUIRED",
        )
    token = secrets.token_urlsafe(24)
    invite = OrgInvite(
        org_id=user.org_id,
        email=payload.email.lower(),
        role=payload.role,
        token=token,
    )
    db.add(invite)
    db.commit()
    org = db.get(Organization, user.org_id)
    email_service.send_email(
        payload.email.lower(),
        f"Invite to {org.name if org else 'organization'}",
        f"You were invited as {payload.role}. Accept with token: {token}\n"
        f"POST /orgs/accept with {{\"token\": \"{token}\"}}",
    )
    return {"message": "Invite sent", "token": token}


@router.post("/accept")
def accept_invite(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token = payload.get("token") if isinstance(payload, dict) else None
    if not token:
        raise ValidationAppError("token required.", code="TOKEN_REQUIRED")
    invite = (
        db.query(OrgInvite)
        .filter(OrgInvite.token == token, OrgInvite.accepted_at.is_(None))
        .first()
    )
    if not invite:
        raise ValidationAppError("Invalid invite.", code="INVALID_INVITE")
    if invite.email != user.email:
        raise AuthorizationError(
            "Invite email mismatch.",
            code="INVITE_EMAIL_MISMATCH",
        )
    user.org_id = invite.org_id
    user.org_role = invite.role
    invite.accepted_at = datetime.utcnow()
    db.commit()
    return {"message": "Joined organization", "org_id": invite.org_id, "role": invite.role}
