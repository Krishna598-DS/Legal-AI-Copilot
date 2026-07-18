"""Centralized error handling — shape, auth, validation, no leak."""

from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test_errors.db"
os.environ["SECRET_KEY"] = "unit-test-secret-key-at-least-32-chars"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
os.environ["OPENAI_API_KEY"] = "sk-test-key-long-enough-for-health"
os.environ["REDIS_URL"] = ""
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["LOG_TO_CONSOLE"] = "false"
os.environ["LOG_TO_FILE"] = "false"

from src.config import clear_settings_cache

clear_settings_cache()

from src.api.main import app
from src.db.database import init_db
from src.errors import (
    AppError,
    AuthenticationError,
    DocumentNotFoundError,
    OpenAIServiceError,
    RetrievalError,
    register_exception_handlers,
)
from src.errors.handlers import error_body

init_db()
client = TestClient(app, raise_server_exceptions=False)


def _assert_error_shape(body: dict):
    assert "error" in body
    err = body["error"]
    assert isinstance(err["code"], str) and err["code"]
    assert isinstance(err["message"], str) and err["message"]
    assert isinstance(err["details"], dict)


def test_error_body_helper():
    payload = error_body("DOCUMENT_NOT_FOUND", "Document not found.", {"id": "x"})
    assert payload == {
        "error": {
            "code": "DOCUMENT_NOT_FOUND",
            "message": "Document not found.",
            "details": {"id": "x"},
        }
    }


def test_app_error_to_dict():
    err = DocumentNotFoundError()
    assert err.to_dict()["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert err.status_code == 404


def test_unauthenticated_standardized():
    r = client.get("/documents")
    assert r.status_code == 401
    body = r.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert "stack" not in str(body).lower()
    assert "traceback" not in str(body).lower()


def test_login_invalid_credentials_shape():
    r = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "wrongpass1"},
    )
    assert r.status_code == 401
    body = r.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


def test_register_validation_error_shape():
    r = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "short",
            "role": "individual",
            "accept_disclaimer": True,
        },
    )
    assert r.status_code == 422
    body = r.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in body["error"]["details"]


def test_document_not_found_shape():
    # register + ask missing doc
    reg = client.post(
        "/auth/register",
        json={
            "email": "erruser@example.com",
            "password": "testpass123",
            "full_name": "Err",
            "role": "individual",
            "accept_disclaimer": True,
        },
    )
    if reg.status_code == 400:
        reg = client.post(
            "/auth/login",
            json={"email": "erruser@example.com", "password": "testpass123"},
        )
    token = reg.json()["access_token"]
    r = client.get(
        "/documents/00000000-0000-0000-0000-000000000099",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    body = r.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert body["error"]["message"] == "Document not found."


def test_unhandled_exception_does_not_leak():
    mini = FastAPI()
    register_exception_handlers(mini)

    @mini.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail xyz")

    c = TestClient(mini, raise_server_exceptions=False)
    r = c.get("/boom")
    assert r.status_code == 500
    body = r.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "secret internal" not in body["error"]["message"]
    assert "xyz" not in str(body)


def test_app_error_handler_on_mini_app():
    mini = FastAPI()
    register_exception_handlers(mini)

    @mini.get("/missing")
    def missing():
        raise DocumentNotFoundError()

    @mini.get("/openai")
    def openai_fail():
        raise OpenAIServiceError(details={"type": "APIError"})

    @mini.get("/retrieval")
    def retrieval_fail():
        raise RetrievalError()

    c = TestClient(mini, raise_server_exceptions=False)

    r = c.get("/missing")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    r = c.get("/openai")
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "OPENAI_ERROR"
    assert r.json()["error"]["details"]["type"] == "APIError"

    r = c.get("/retrieval")
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "RETRIEVAL_ERROR"


def test_sqlalchemy_error_mapped():
    mini = FastAPI()
    register_exception_handlers(mini)

    @mini.get("/db")
    def db_fail():
        raise SQLAlchemyError("connection refused internal host")

    c = TestClient(mini, raise_server_exceptions=False)
    r = c.get("/db")
    assert r.status_code == 503
    body = r.json()
    _assert_error_shape(body)
    assert body["error"]["code"] == "DATABASE_ERROR"
    assert "connection refused" not in body["error"]["message"]
    assert "internal host" not in str(body)


def test_authentication_error_headers_optional():
    err = AuthenticationError("Not authenticated.")
    assert err.to_dict()["error"]["code"] == "AUTHENTICATION_REQUIRED"
