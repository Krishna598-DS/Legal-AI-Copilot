"""User persona / role field — signup, profile, backward compatibility."""

from __future__ import annotations

import os
import tempfile

from fastapi.testclient import TestClient

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test_personas.db"
os.environ["SECRET_KEY"] = "unit-test-secret-key-at-least-32-chars"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
os.environ["OPENAI_API_KEY"] = "sk-test-key-long-enough"
os.environ["REDIS_URL"] = ""
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["LOG_TO_CONSOLE"] = "false"
os.environ["LOG_TO_FILE"] = "false"

from src.config import clear_settings_cache

clear_settings_cache()

from src.api.main import app
from src.auth.personas import (
    ALLOWED_ROLES,
    DEFAULT_ROLE,
    normalize_role,
    role_label,
    welcome_message,
)
from src.db.database import SessionLocal, init_db
from src.db.models import User

init_db()
client = TestClient(app)


def test_persona_helpers():
    assert DEFAULT_ROLE == "individual"
    assert "lawyer" in ALLOWED_ROLES
    assert normalize_role(None) == "individual"
    assert normalize_role("Lawyer") == "lawyer"
    assert normalize_role("chartered accountant") == "chartered_accountant"
    assert role_label("student") == "Student"
    assert "employment" in welcome_message("hr_professional").lower()


def test_register_requires_role():
    r = client.post(
        "/auth/register",
        json={
            "email": "norole@example.com",
            "password": "testpass123",
            "accept_disclaimer": True,
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_invalid_role():
    r = client.post(
        "/auth/register",
        json={
            "email": "badrole@example.com",
            "password": "testpass123",
            "role": "astronaut",
            "accept_disclaimer": True,
        },
    )
    assert r.status_code == 422


def test_register_stores_role_and_profile_returns_it():
    email = "persona-lawyer@example.com"
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "testpass123",
            "full_name": "Ada Counsel",
            "role": "lawyer",
            "accept_disclaimer": True,
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "lawyer"
    assert body["role_label"] == "Lawyer"
    assert "briefing" in body["welcome_message"].lower() or "counsel" in body["welcome_message"].lower()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.role == "lawyer"
    finally:
        db.close()


def test_each_supported_role_can_register():
    for role in sorted(ALLOWED_ROLES):
        email = f"{role}@persona-test.example"
        r = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "testpass123",
                "role": role,
                "accept_disclaimer": True,
            },
        )
        assert r.status_code == 201, (role, r.text)
        token = r.json()["access_token"]
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["role"] == role
        assert me.json()["role_label"] == role_label(role)
        assert me.json()["welcome_message"] == welcome_message(role)


def test_legacy_user_without_role_defaults_on_profile():
    """Existing rows with missing/empty role surface as individual."""
    db = SessionLocal()
    try:
        user = User(
            email="legacy@example.com",
            hashed_password="not-used",
            email_verified=True,
            role="individual",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        # Simulate pre-migration empty value read path via normalize
        user.role = ""
        db.commit()
        user_id = user.id
    finally:
        db.close()

    from src.auth.security import create_access_token

    token = create_access_token(user_id)
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "individual"
    assert me.json()["role_label"] == "Individual"


def test_auth_still_works_unchanged_for_login():
    email = "login-persona@example.com"
    password = "testpass123"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "role": "student",
            "accept_disclaimer": True,
        },
    )
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    assert "access_token" in r.json()
