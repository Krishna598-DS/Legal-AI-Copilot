"""Local/manual professional directory backed by SQLAlchemy."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models import LegalProfessional


def _to_dict(row: LegalProfessional) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "specialization": row.specialization,
        "city": row.city,
        "state": row.state or "",
        "country": row.country or "",
        "phone": row.phone,
        "email": row.email,
        "website": row.website,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "verified": bool(row.verified),
        "source": row.source or "manual",
        "external_id": row.external_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class LocalDirectoryProvider:
    """Administrator-populated directory stored in the app database."""

    name = "local"

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_professionals(
        self,
        *,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        q = self.db.query(LegalProfessional)
        if verified_only:
            q = q.filter(LegalProfessional.verified.is_(True))
        rows = (
            q.order_by(
                LegalProfessional.verified.desc(),
                LegalProfessional.name.asc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return [_to_dict(r) for r in rows]

    def search_by_specialization(
        self,
        specialization: str,
        *,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        needle = (specialization or "").strip()
        if not needle:
            return []
        q = self.db.query(LegalProfessional).filter(
            func.lower(LegalProfessional.specialization) == needle.lower()
        )
        if verified_only:
            q = q.filter(LegalProfessional.verified.is_(True))
        rows = (
            q.order_by(
                LegalProfessional.verified.desc(),
                LegalProfessional.city.asc(),
                LegalProfessional.name.asc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return [_to_dict(r) for r in rows]

    def search_by_city(
        self,
        city: str,
        *,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        needle = (city or "").strip()
        if not needle:
            return []
        q = self.db.query(LegalProfessional).filter(
            func.lower(LegalProfessional.city) == needle.lower()
        )
        if verified_only:
            q = q.filter(LegalProfessional.verified.is_(True))
        rows = (
            q.order_by(
                LegalProfessional.verified.desc(),
                LegalProfessional.specialization.asc(),
                LegalProfessional.name.asc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return [_to_dict(r) for r in rows]

    def get_professional(self, professional_id: str) -> dict[str, Any] | None:
        row = self.db.get(LegalProfessional, professional_id)
        return _to_dict(row) if row else None

    def create_professional(self, data: dict[str, Any]) -> dict[str, Any]:
        row = LegalProfessional(
            name=str(data["name"]).strip(),
            specialization=str(data["specialization"]).strip(),
            city=str(data["city"]).strip(),
            state=str(data.get("state") or "").strip(),
            country=str(data.get("country") or "").strip(),
            phone=(str(data["phone"]).strip() if data.get("phone") else None),
            email=(str(data["email"]).strip() if data.get("email") else None),
            website=(str(data["website"]).strip() if data.get("website") else None),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            verified=bool(data.get("verified", False)),
            source=str(data.get("source") or "manual"),
            external_id=data.get("external_id"),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_dict(row)

    def update_professional(
        self, professional_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        row = self.db.get(LegalProfessional, professional_id)
        if not row:
            return None
        for field in (
            "name",
            "specialization",
            "city",
            "state",
            "country",
            "phone",
            "email",
            "website",
            "latitude",
            "longitude",
            "verified",
            "source",
            "external_id",
        ):
            if field in data and data[field] is not None:
                setattr(row, field, data[field])
            elif field in data and field in {
                "phone",
                "email",
                "website",
                "latitude",
                "longitude",
                "external_id",
            }:
                setattr(row, field, None)
        self.db.commit()
        self.db.refresh(row)
        return _to_dict(row)

    def delete_professional(self, professional_id: str) -> bool:
        row = self.db.get(LegalProfessional, professional_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True
