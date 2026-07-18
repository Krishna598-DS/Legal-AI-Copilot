"""Production health / readiness checks."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import text

from src.config import get_settings
from src.db.database import engine


def _check_database() -> tuple[str, str | None]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok", None
    except Exception as exc:
        return "error", str(exc)


def _check_storage() -> tuple[str, str | None]:
    settings = get_settings()
    missing: list[str] = []
    for label, path in (
        ("upload_dir", settings.UPLOAD_DIR),
        ("index_dir", settings.INDEX_DIR),
    ):
        if not path or not os.path.isdir(path):
            missing.append(label)
    if missing:
        return "error", f"missing directories: {', '.join(missing)}"
    return "ok", None


def _check_openai() -> tuple[str, str | None]:
    settings = get_settings()
    key = (settings.OPENAI_API_KEY or "").strip()
    if not key:
        return "error", "OPENAI_API_KEY is not configured"
    if key.startswith("sk-") and len(key) < 20:
        return "error", "OPENAI_API_KEY looks invalid"
    return "ok", None


def _check_faiss() -> tuple[str, str | None]:
    try:
        import faiss  # noqa: F401
    except Exception as exc:
        return "error", f"faiss import failed: {exc}"
    try:
        from langchain_community.vectorstores import FAISS  # noqa: F401
    except Exception as exc:
        return "error", f"langchain FAISS unavailable: {exc}"
    return "ok", None


def run_checks() -> dict[str, Any]:
    """
    Run dependency checks and return a structured health payload.

    Status:
      - healthy   — all checks ok
      - degraded  — non-critical failure (openai missing still allows process up)
      - unhealthy — database, storage, or faiss failed
    """
    results: dict[str, str] = {}
    details: dict[str, str] = {}

    for name, fn in (
        ("database", _check_database),
        ("storage", _check_storage),
        ("openai", _check_openai),
        ("faiss", _check_faiss),
    ):
        status, detail = fn()
        results[name] = status
        if detail:
            details[name] = detail

    failed = [name for name, value in results.items() if value != "ok"]
    overall = "healthy" if not failed else "unhealthy"

    settings = get_settings()
    payload: dict[str, Any] = {
        "status": overall,
        "checks": results,
        "version": settings.APP_VERSION,
    }
    if details:
        payload["details"] = details
    return payload


def is_ready(payload: dict[str, Any] | None = None) -> bool:
    """Ready when all dependency checks report ok."""
    data = payload or run_checks()
    checks = data.get("checks") or {}
    return all(
        checks.get(name) == "ok"
        for name in ("database", "storage", "openai", "faiss")
    )
