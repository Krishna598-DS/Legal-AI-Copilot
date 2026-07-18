"""Professional directory foundation tests (local provider, no external APIs)."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test_professionals.db"
os.environ["SECRET_KEY"] = "unit-test-secret-key-at-least-32-chars"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-test")
os.environ["REDIS_URL"] = ""
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["DIRECTORY_PROVIDER"] = "local"

from src.config import clear_settings_cache

clear_settings_cache()

from src.api.main import app
from src.db.database import SessionLocal, init_db
from src.directory.local import LocalDirectoryProvider
from src.directory.service import get_directory_provider

init_db()
client = TestClient(app)


def _register(email: str, password: str = "testpass123") -> dict:
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Dir Tester",
            "role": "individual",
            "accept_disclaimer": True,
        },
    )
    if r.status_code in (400, 409) or "already" in r.text.lower():
        r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def user_headers():
    return _register("user-dir@example.com")


@pytest.fixture
def admin_headers():
    return _register("admin@example.com")


def test_local_provider_crud():
    db = SessionLocal()
    try:
        provider = LocalDirectoryProvider(db)
        created = provider.create_professional(
            {
                "name": "Asha Property",
                "specialization": "Property Lawyer",
                "city": "Mumbai",
                "state": "MH",
                "country": "India",
                "verified": True,
            }
        )
        assert created["id"]
        assert created["source"] == "manual"
        by_spec = provider.search_by_specialization("property lawyer")
        assert len(by_spec) >= 1
        by_city = provider.search_by_city("mumbai")
        assert any(p["name"] == "Asha Property" for p in by_city)
        listed = provider.list_professionals(verified_only=True)
        assert any(p["id"] == created["id"] for p in listed)
        assert provider.delete_professional(created["id"]) is True
    finally:
        db.close()


def test_factory_returns_local():
    db = SessionLocal()
    try:
        provider = get_directory_provider(db)
        assert provider.name == "local"
    finally:
        db.close()


def test_admin_create_and_public_search(admin_headers, user_headers):
    payload = {
        "name": "Ravi Corporate",
        "specialization": "Corporate Lawyer",
        "city": "Bengaluru",
        "state": "KA",
        "country": "India",
        "email": "ravi@example.com",
        "phone": "+910000000000",
        "website": "https://example.com",
        "latitude": 12.97,
        "longitude": 77.59,
        "verified": True,
    }
    r = client.post(
        "/admin/professionals", headers=admin_headers, json=payload
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["specialization"] == "Corporate Lawyer"
    assert body["verified"] is True

    listed = client.get("/professionals", headers=user_headers)
    assert listed.status_code == 200
    assert any(p["name"] == "Ravi Corporate" for p in listed.json())

    by_spec = client.get(
        "/professionals/search",
        headers=user_headers,
        params={"specialization": "Corporate Lawyer"},
    )
    assert by_spec.status_code == 200
    assert any(p["city"] == "Bengaluru" for p in by_spec.json())

    by_city = client.get(
        "/professionals/by-city/Bengaluru",
        headers=user_headers,
    )
    assert by_city.status_code == 200
    assert any(p["specialization"] == "Corporate Lawyer" for p in by_city.json())

    path_spec = client.get(
        "/professionals/by-specialization/Corporate%20Lawyer",
        headers=user_headers,
    )
    assert path_spec.status_code == 200
    assert len(path_spec.json()) >= 1


def test_search_requires_filter(user_headers):
    r = client.get("/professionals/search", headers=user_headers)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "PROFESSIONAL_SEARCH_REQUIRED"


def test_non_admin_cannot_create(user_headers):
    r = client.post(
        "/admin/professionals",
        headers=user_headers,
        json={
            "name": "Nope",
            "specialization": "Civil Lawyer",
            "city": "Delhi",
        },
    )
    assert r.status_code == 403


def test_recommend_by_city_and_location(admin_headers, user_headers):
    client.post(
        "/admin/professionals",
        headers=admin_headers,
        json={
            "name": "Near Property",
            "specialization": "Property Lawyer",
            "city": "Mumbai",
            "latitude": 19.08,
            "longitude": 72.88,
            "verified": True,
        },
    )
    by_city = client.get(
        "/professionals/recommend",
        headers=user_headers,
        params={"specialization": "Property Lawyer", "city": "Mumbai"},
    )
    assert by_city.status_code == 200, by_city.text
    assert any(p["name"] == "Near Property" for p in by_city.json())
    assert by_city.json()[0]["distance_km"] == 0.0

    near = client.get(
        "/professionals/recommend",
        headers=user_headers,
        params={
            "specialization": "Property Lawyer",
            "latitude": 19.076,
            "longitude": 72.877,
        },
    )
    assert near.status_code == 200, near.text
    body = near.json()
    assert body
    assert body[0]["practice_area"] == "Property Lawyer"
    assert body[0]["distance_km"] is not None
    assert "name" in body[0]
