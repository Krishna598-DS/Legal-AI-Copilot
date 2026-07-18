"""Factory + facade for the professional directory."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.directory.base import ProfessionalDirectoryProvider
from src.directory.local import LocalDirectoryProvider
from src.directory.ranking import rank_professionals
from src.errors import ValidationAppError


def get_directory_provider(db: Session) -> ProfessionalDirectoryProvider:
    """
    Return the configured directory provider.

    Today only ``local`` (manual DB) is implemented. External directory
    integrations should register here without changing API routes.
    """
    settings = get_settings()
    provider = (settings.DIRECTORY_PROVIDER or "local").strip().lower()
    if provider == "local":
        return LocalDirectoryProvider(db)
    raise ValidationAppError(
        f"Unsupported directory provider: {provider}. "
        "Configure DIRECTORY_PROVIDER=local until an external adapter is added.",
        code="DIRECTORY_PROVIDER_UNSUPPORTED",
        details={"provider": provider},
    )


def recommend_professionals(
    db: Session,
    *,
    specialization: str | None = None,
    city: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    max_distance_km: float | None = None,
    verified_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Recommend professionals near the user and/or in a city.

    Location coordinates must be supplied by the client only after the user
    grants permission — this function never obtains device location itself.
    """
    has_location = latitude is not None and longitude is not None
    city_q = (city or "").strip() or None
    spec_q = (specialization or "").strip() or None

    if not has_location and not city_q and not spec_q:
        raise ValidationAppError(
            "Provide a city, specialization, or user location (after permission).",
            code="PROFESSIONAL_RECOMMEND_REQUIRED",
        )
    if (latitude is None) ^ (longitude is None):
        raise ValidationAppError(
            "Both latitude and longitude are required when using location.",
            code="LOCATION_INCOMPLETE",
        )

    provider = get_directory_provider(db)
    # Broad fetch; ranking applies distance / specialization / verification.
    candidates = provider.list_professionals(
        verified_only=verified_only, limit=500, offset=0
    )
    ranked = rank_professionals(
        candidates,
        specialization=spec_q,
        latitude=latitude,
        longitude=longitude,
        city=city_q,
        max_distance_km=max_distance_km,
    )
    return ranked[: max(1, min(limit, 200))]
