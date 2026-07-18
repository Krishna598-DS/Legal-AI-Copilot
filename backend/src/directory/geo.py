"""Geo helpers for professional discovery (no external geocoding APIs)."""

from __future__ import annotations

import math


def haversine_km(
    lat1: float | None,
    lon1: float | None,
    lat2: float | None,
    lon2: float | None,
) -> float | None:
    """Great-circle distance in kilometers, or None if any coordinate is missing."""
    try:
        if None in (lat1, lon1, lat2, lon2):
            return None
        a1, o1, a2, o2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (TypeError, ValueError):
        return None

    r = 6371.0
    p1, p2 = math.radians(a1), math.radians(a2)
    dp = math.radians(a2 - a1)
    dl = math.radians(o2 - o1)
    h = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )
    return round(2 * r * math.asin(min(1.0, math.sqrt(h))), 2)
