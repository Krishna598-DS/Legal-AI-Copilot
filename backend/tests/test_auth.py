"""Auth and isolation tests (no OpenAI required for auth paths)."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Isolate DB before importing app
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SECRET_KEY"] = "unit-test-secret-key-at-least-32-chars"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-test")
os.environ["REDIS_URL"] = ""
os.environ["LOG_LEVEL"] = "WARNING"

from src.config import clear_settings_cache, get_settings

clear_settings_cache()

from src.api.main import app
from src.db.database import init_db

init_db()
client = TestClient(app)


@pytest.fixture
def auth_headers():
    email = "tester@example.com"
    password = "testpass123"
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Tester",
            "role": "lawyer",
            "accept_disclaimer": True,
        },
    )
    if r.status_code == 400 and "already" in r.text.lower():
        r = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
    assert r.status_code in (200, 201), r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health():
    r = client.get("/health")
    assert r.status_code in (200, 503)
    body = r.json()
    assert body["status"] in {"healthy", "unhealthy"}
    assert set(body["checks"]) >= {"database", "storage", "openai", "faiss"}


def test_register_requires_disclaimer():
    r = client.post(
        "/auth/register",
        json={
            "email": "nodisc@example.com",
            "password": "testpass123",
            "role": "individual",
            "accept_disclaimer": False,
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "DISCLAIMER_REQUIRED"


def test_me(auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "tester@example.com"
    assert body["terms_version"]
    assert body["role"] == "lawyer"
    assert body["role_label"] == "Lawyer"
    assert len(body["welcome_message"]) > 20


def test_documents_isolated_empty(auth_headers):
    r = client.get("/documents", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_ask_requires_auth():
    r = client.post(
        "/ask", json={"question": "What is payment?", "document_id": "x"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_forgot_password():
    r = client.post(
        "/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert r.status_code == 200


def test_privacy_and_disclaimer():
    assert client.get("/account/privacy").status_code == 200
    assert client.get("/account/disclaimer").status_code == 200


def test_org_create(auth_headers):
    r = client.post("/orgs", json={"name": "Acme Legal"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    r2 = client.get("/orgs/me", headers=auth_headers)
    assert r2.json()["organization"]["name"] == "Acme Legal"
