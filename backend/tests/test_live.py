"""Minimal CI smoke tests (no external OpenAI calls)."""

from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_live_endpoint():
    res = client.get("/live")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "alive"
    assert "version" in body


def test_api_info():
    res = client.get("/api")
    assert res.status_code == 200
    body = res.json()
    assert "health" in body
    assert "docs" in body
