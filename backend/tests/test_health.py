"""Production health / ready / live endpoint tests."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient

_tmp = tempfile.mkdtemp()
_upload = os.path.join(_tmp, "uploads")
_index = os.path.join(_tmp, "indexes")
os.makedirs(_upload, exist_ok=True)
os.makedirs(_index, exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test_health.db"
os.environ["SECRET_KEY"] = "unit-test-secret-key-at-least-32-chars"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
os.environ["OPENAI_API_KEY"] = "sk-test-key-long-enough-for-health"
os.environ["REDIS_URL"] = ""
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["LOG_TO_CONSOLE"] = "false"
os.environ["LOG_TO_FILE"] = "false"
os.environ["DATA_DIR"] = _tmp
os.environ["UPLOAD_DIR"] = _upload
os.environ["INDEX_DIR"] = _index

from src.config import clear_settings_cache

clear_settings_cache()

from src.api.main import app
from src.db.database import init_db
from src.services import health_service

init_db()
client = TestClient(app)

_HEALTHY = {
    "status": "healthy",
    "checks": {
        "database": "ok",
        "storage": "ok",
        "openai": "ok",
        "faiss": "ok",
    },
    "version": "test",
}


def test_live_always_ok():
    r = client.get("/live")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "alive"
    assert "version" in body


def test_health_structured_shape():
    with patch.object(health_service, "run_checks", return_value=_HEALTHY):
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "status": "healthy",
        "checks": {
            "database": "ok",
            "storage": "ok",
            "openai": "ok",
            "faiss": "ok",
        },
        "version": "test",
        "details": {},
    }


def test_ready_ok():
    with patch.object(health_service, "run_checks", return_value=_HEALTHY):
        r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    assert r.json()["checks"]["database"] == "ok"


def test_ready_returns_503_when_storage_missing():
    payload = {
        "status": "unhealthy",
        "checks": {
            "database": "ok",
            "storage": "error",
            "openai": "ok",
            "faiss": "ok",
        },
        "version": "test",
        "details": {"storage": "missing directories: upload_dir"},
    }
    with patch.object(health_service, "run_checks", return_value=payload):
        r = client.get("/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "unhealthy"
    assert body["checks"]["storage"] == "error"
    assert "upload_dir" in body["details"]["storage"]


def test_health_returns_503_when_openai_missing():
    payload = {
        "status": "unhealthy",
        "checks": {
            "database": "ok",
            "storage": "ok",
            "openai": "error",
            "faiss": "ok",
        },
        "version": "test",
        "details": {"openai": "OPENAI_API_KEY is not configured"},
    }
    with patch.object(health_service, "run_checks", return_value=payload):
        r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["checks"]["openai"] == "error"


def test_run_checks_openai_missing():
    with patch.object(
        health_service,
        "_check_openai",
        return_value=("error", "OPENAI_API_KEY is not configured"),
    ):
        with patch.object(
            health_service, "_check_database", return_value=("ok", None)
        ):
            with patch.object(
                health_service, "_check_storage", return_value=("ok", None)
            ):
                with patch.object(
                    health_service, "_check_faiss", return_value=("ok", None)
                ):
                    payload = health_service.run_checks()
    assert payload["status"] == "unhealthy"
    assert payload["checks"]["openai"] == "error"
    assert health_service.is_ready(payload) is False


def test_check_storage_detects_missing_dir(tmp_path):
    missing = tmp_path / "does-not-exist"
    with patch("src.services.health_service.get_settings") as gs:
        settings = gs.return_value
        settings.UPLOAD_DIR = str(missing)
        settings.INDEX_DIR = str(tmp_path / "indexes")
        (tmp_path / "indexes").mkdir()
        status, detail = health_service._check_storage()
    assert status == "error"
    assert detail and "upload_dir" in detail


def test_check_database_ok():
    status, detail = health_service._check_database()
    assert status == "ok"
    assert detail is None


def test_api_info_lists_probes():
    r = client.get("/api")
    assert r.status_code == 200
    body = r.json()
    assert body["health"] == "/health"
    assert body["ready"] == "/ready"
    assert body["live"] == "/live"
