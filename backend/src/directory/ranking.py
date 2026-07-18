"""Rank professional recommendations by distance, specialization, verification."""

from __future__ import annotations

from typing import Any

from src.directory.geo import haversine_km


def specialization_match_score(
    professional_spec: str | None, target: str | None
) -> float:
    """
    1.0 exact match, 0.6 substring match, else 0.0.
    Used for sorting — never invents a specialization.
    """
    if not target or not str(target).strip():
        return 0.0
    left = (professional_spec or "").strip().lower()
    right = str(target).strip().lower()
    if not left:
        return 0.0
    if left == right:
        return 1.0
    if right in left or left in right:
        return 0.6
    return 0.0


def rank_professionals(
    professionals: list[dict[str, Any]],
    *,
    specialization: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    city: str | None = None,
    max_distance_km: float | None = None,
) -> list[dict[str, Any]]:
    """
    Enrich and sort professionals.

    Sort order (ascending priority):
    1. Distance (nearest first; missing distance last)
    2. Specialization match (higher first)
    3. Verified (verified first)
    """
    has_user_location = latitude is not None and longitude is not None
    city_needle = (city or "").strip().lower() or None

    enriched: list[dict[str, Any]] = []
    for raw in professionals:
        row = dict(raw)
        spec_score = specialization_match_score(
            row.get("specialization"), specialization
        )
        city_match = bool(
            city_needle and (row.get("city") or "").strip().lower() == city_needle
        )

        distance: float | None = None
        if has_user_location:
            distance = haversine_km(
                latitude,
                longitude,
                row.get("latitude"),
                row.get("longitude"),
            )
        elif city_match:
            # Manual city search: treat city matches as "local" (0 km).
            distance = 0.0

        if max_distance_km is not None and distance is not None:
            if distance > float(max_distance_km):
                continue

        # When user searched by city without coords, keep only that city.
        if city_needle and not has_user_location and not city_match:
            continue

        # Prefer specialization matches when a target category is set, but still
        # allow near-me results with weaker match so nearby verified pros surface.
        row["practice_area"] = row.get("specialization") or ""
        row["distance_km"] = distance
        row["specialization_match"] = spec_score
        row["city_match"] = city_match
        enriched.append(row)

    if specialization and has_user_location:
        # Keep exact/partial matches first pool; if empty, fall back to all ranked.
        matched = [r for r in enriched if r["specialization_match"] > 0]
        if matched:
            enriched = matched

    enriched.sort(
        key=lambda r: (
            r["distance_km"] is None,
            r["distance_km"] if r["distance_km"] is not None else 1e12,
            -float(r["specialization_match"]),
            0 if r.get("verified") else 1,
            (r.get("name") or "").lower(),
        )
    )
    return enriched
