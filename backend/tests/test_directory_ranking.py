"""Tests for geo distance + professional recommendation ranking."""

from __future__ import annotations

from src.directory.geo import haversine_km
from src.directory.ranking import rank_professionals, specialization_match_score


def test_haversine_nearby():
    # Roughly ~1.1 km between close Mumbai points
    d = haversine_km(19.076, 72.877, 19.086, 72.877)
    assert d is not None
    assert 0.5 < d < 2.5


def test_haversine_missing_coords():
    assert haversine_km(19.0, 72.0, None, 72.0) is None


def test_specialization_match_score():
    assert specialization_match_score("Property Lawyer", "Property Lawyer") == 1.0
    assert specialization_match_score("Corporate Lawyer", "Property Lawyer") == 0.0
    assert specialization_match_score("Senior Property Lawyer", "Property") == 0.6


def test_rank_by_distance_then_spec_then_verified():
    pros = [
        {
            "id": "1",
            "name": "Far Unverified",
            "specialization": "Property Lawyer",
            "city": "Pune",
            "latitude": 18.52,
            "longitude": 73.85,
            "verified": False,
        },
        {
            "id": "2",
            "name": "Near Verified",
            "specialization": "Property Lawyer",
            "city": "Mumbai",
            "latitude": 19.08,
            "longitude": 72.88,
            "verified": True,
        },
        {
            "id": "3",
            "name": "Near Other Spec",
            "specialization": "Tax Lawyer",
            "city": "Mumbai",
            "latitude": 19.07,
            "longitude": 72.87,
            "verified": True,
        },
        {
            "id": "4",
            "name": "Near Unverified Same Spec",
            "specialization": "Property Lawyer",
            "city": "Mumbai",
            "latitude": 19.09,
            "longitude": 72.88,
            "verified": False,
        },
    ]
    ranked = rank_professionals(
        pros,
        specialization="Property Lawyer",
        latitude=19.076,
        longitude=72.877,
    )
    ids = [p["id"] for p in ranked]
    # Only specialization matches kept when location + specialization provided
    assert "3" not in ids
    assert ids[0] in {"2", "4"}
    assert ranked[0]["distance_km"] is not None
    # Among property lawyers, nearer first; verified breaks near-ties after distance
    assert all(p["practice_area"] == "Property Lawyer" for p in ranked)


def test_city_search_without_location():
    pros = [
        {
            "id": "a",
            "name": "Delhi Pro",
            "specialization": "Civil Lawyer",
            "city": "Delhi",
            "latitude": None,
            "longitude": None,
            "verified": False,
        },
        {
            "id": "b",
            "name": "Mumbai Pro",
            "specialization": "Civil Lawyer",
            "city": "Mumbai",
            "latitude": None,
            "longitude": None,
            "verified": True,
        },
    ]
    ranked = rank_professionals(
        pros, specialization="Civil Lawyer", city="Mumbai"
    )
    assert len(ranked) == 1
    assert ranked[0]["id"] == "b"
    assert ranked[0]["distance_km"] == 0.0
    assert ranked[0]["city_match"] is True
