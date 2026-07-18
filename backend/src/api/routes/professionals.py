"""Public professional discovery APIs (no external directory yet)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.auth.schemas import ProfessionalRecommendResponse, ProfessionalResponse
from src.db.database import get_db
from src.db.models import User
from src.directory import get_directory_provider
from src.directory.service import recommend_professionals
from src.errors import ValidationAppError

router = APIRouter(prefix="/professionals", tags=["professionals"])


@router.get("", response_model=list[ProfessionalResponse])
def list_professionals(
    verified_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List professionals from the configured directory provider."""
    provider = get_directory_provider(db)
    rows = provider.list_professionals(
        verified_only=verified_only, limit=limit, offset=offset
    )
    return [ProfessionalResponse(**r) for r in rows]


@router.get("/recommend", response_model=list[ProfessionalRecommendResponse])
def recommend_near_or_city(
    specialization: str | None = Query(
        default=None,
        description="Recommended expert category / practice area",
    ),
    city: str | None = Query(
        default=None,
        description="Manual city search when location is unavailable",
    ),
    latitude: float | None = Query(
        default=None,
        ge=-90,
        le=90,
        description="User latitude — only send after explicit permission",
    ),
    longitude: float | None = Query(
        default=None,
        ge=-180,
        le=180,
        description="User longitude — only send after explicit permission",
    ),
    max_distance_km: float | None = Query(
        default=None,
        ge=0,
        le=20000,
        description="Optional distance cap when using location",
    ),
    verified_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Recommend professionals sorted by distance, specialization match, verification.

    The API never reads device location. Clients must request permission first
    and only then pass latitude/longitude. If location is unavailable, pass city.
    """
    rows = recommend_professionals(
        db,
        specialization=specialization,
        city=city,
        latitude=latitude,
        longitude=longitude,
        max_distance_km=max_distance_km,
        verified_only=verified_only,
        limit=limit,
    )
    return [ProfessionalRecommendResponse(**r) for r in rows]


@router.get("/search", response_model=list[ProfessionalResponse])
def search_professionals(
    specialization: str | None = Query(
        default=None,
        description="Exact specialization / expert category (e.g. Property Lawyer)",
    ),
    city: str | None = Query(default=None, description="Exact city name"),
    verified_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search professionals by specialization and/or city.

    Provide at least one of ``specialization`` or ``city``.
    When both are set, results must match both filters.
    """
    spec = (specialization or "").strip() or None
    city_q = (city or "").strip() or None
    if not spec and not city_q:
        raise ValidationAppError(
            "Provide specialization and/or city to search.",
            code="PROFESSIONAL_SEARCH_REQUIRED",
        )

    provider = get_directory_provider(db)
    if spec and not city_q:
        rows = provider.search_by_specialization(
            spec, verified_only=verified_only, limit=limit, offset=offset
        )
    elif city_q and not spec:
        rows = provider.search_by_city(
            city_q, verified_only=verified_only, limit=limit, offset=offset
        )
    else:
        # Intersection of both filters (local provider does exact match).
        by_spec = {
            r["id"]: r
            for r in provider.search_by_specialization(
                spec, verified_only=verified_only, limit=500, offset=0
            )
        }
        rows = [
            r
            for r in provider.search_by_city(
                city_q, verified_only=verified_only, limit=500, offset=0
            )
            if r["id"] in by_spec
        ]
        rows = rows[offset : offset + limit]

    return [ProfessionalResponse(**r) for r in rows]


@router.get("/by-specialization/{specialization}", response_model=list[ProfessionalResponse])
def search_by_specialization(
    specialization: str,
    verified_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Convenience path: search by specialization only."""
    provider = get_directory_provider(db)
    rows = provider.search_by_specialization(
        specialization,
        verified_only=verified_only,
        limit=limit,
        offset=offset,
    )
    return [ProfessionalResponse(**r) for r in rows]


@router.get("/by-city/{city}", response_model=list[ProfessionalResponse])
def search_by_city(
    city: str,
    verified_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Convenience path: search by city only."""
    provider = get_directory_provider(db)
    rows = provider.search_by_city(
        city, verified_only=verified_only, limit=limit, offset=offset
    )
    return [ProfessionalResponse(**r) for r in rows]
