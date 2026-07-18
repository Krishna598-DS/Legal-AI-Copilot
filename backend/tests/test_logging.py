"""Structured JSON logging + request_id middleware tests."""

from __future__ import annotations

import json
import logging
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test_logging.db"
os.environ["SECRET_KEY"] = "unit-test-secret-key-at-least-32-chars"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-test")
os.environ["REDIS_URL"] = ""
os.environ["LOG_LEVEL"] = "INFO"
os.environ["LOG_FORMAT"] = "json"
os.environ["LOG_TO_CONSOLE"] = "false"
os.environ["LOG_TO_FILE"] = "false"

from src.config import clear_settings_cache

clear_settings_cache()

from src.api.main import app
from src.db.database import init_db
from src.logging_config import setup_logging
from src.observability.context import reset_request_id, set_request_id
from src.observability.events import log_event
from src.observability.formatter import JsonFormatter

init_db()
setup_logging(force=True)
client = TestClient(app)


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.setFormatter(JsonFormatter())

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def capture_logs():
    logger = setup_logging(force=True)
    handler = _ListHandler()
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


def test_json_formatter_includes_core_fields():
    record = logging.LogRecord(
        name="legal_rag",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.event = "login"
    record.request_id = "abc123"
    record.user_id = "user-1"
    record.endpoint = "/auth/login"

    line = JsonFormatter().format(record)
    payload = json.loads(line)
    assert payload["level"] == "INFO"
    assert payload["message"] == "hello"
    assert payload["event"] == "login"
    assert payload["request_id"] == "abc123"
    assert payload["user_id"] == "user-1"
    assert payload["endpoint"] == "/auth/login"
    assert "timestamp" in payload


def test_log_event_attaches_context(capture_logs):
    token = set_request_id("req-ctx-1")
    try:
        log_event(
            logging.getLogger("legal_rag"),
            "retrieval",
            message="chunks retrieved",
            chunk_count=3,
            user_id="u-9",
        )
    finally:
        reset_request_id(token)

    assert capture_logs.records
    record = capture_logs.records[-1]
    line = capture_logs.format(record)
    payload = json.loads(line)
    assert payload["event"] == "retrieval"
    assert payload["request_id"] == "req-ctx-1"
    assert payload["user_id"] == "u-9"
    assert payload["chunk_count"] == 3


def test_health_sets_request_id_header(capture_logs):
    response = client.get("/health")
    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert len(request_id) >= 8

    http_lines = [
        json.loads(capture_logs.format(r))
        for r in capture_logs.records
        if getattr(r, "event", None) == "http_request"
    ]
    assert http_lines
    last = http_lines[-1]
    assert last["endpoint"] == "/health"
    assert last["method"] == "GET"
    assert last["status_code"] == 200
    assert last["request_id"] == request_id
    assert "latency_ms" in last


def test_honors_incoming_request_id():
    response = client.get("/health", headers={"X-Request-ID": "fixed-id-42"})
    assert response.headers.get("X-Request-ID") == "fixed-id-42"


def test_login_emits_login_event(capture_logs):
    email = "logging-user@example.com"
    password = "testpass123"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Log User",
            "role": "individual",
            "accept_disclaimer": True,
        },
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200

    events = {
        getattr(r, "event", None)
        for r in capture_logs.records
    }
    assert "login" in events

    token = response.json()["access_token"]
    logout = client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert logout.status_code == 200
    events = {getattr(r, "event", None) for r in capture_logs.records}
    assert "logout" in events
