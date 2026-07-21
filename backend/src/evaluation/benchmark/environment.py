"""
Isolated runtime environment for benchmark evaluation runs.

The benchmark harness reuses the real production service layer (``document_service``,
``rag_service``) rather than re-implementing ingestion or retrieval — but it must never
run against the production database, uploads, or FAISS indexes. This module forces the
process to use a dedicated SQLite database and dedicated upload/index/log directories
under ``evaluation/benchmark/.state/`` *before* any other part of the application is
imported, since ``src.config.get_settings()`` is cached process-wide on first call.

This file must be the first `src.*` import in any benchmark entrypoint.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BENCHMARK_DIR = REPO_ROOT / "evaluation" / "benchmark"
_STATE_DIR = BENCHMARK_DIR / ".state"

# Force (not setdefault) — an ambient DATABASE_URL/DATA_DIR from the caller's shell
# must never leak into an evaluation run; isolation is not optional here.
os.environ["DATABASE_URL"] = f"sqlite:///{(_STATE_DIR / 'eval.db').as_posix()}"
os.environ["DATA_DIR"] = str(_STATE_DIR / "data")
os.environ["LOG_DIR"] = str(_STATE_DIR / "logs")

# Everything below this line may safely import the rest of the application — the
# isolation overrides above are already in place.

import io  # noqa: E402
from datetime import datetime  # noqa: E402

from fastapi import UploadFile  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.db.database import SessionLocal, init_db  # noqa: E402
from src.db.models import Document, User  # noqa: E402
from src.services import document_service, rag_service  # noqa: E402

BENCHMARK_USER_EMAIL = "benchmark-harness@eval.local"

settings = get_settings()


def ensure_environment() -> None:
    """Create tables / runtime directories for the isolated eval database."""
    init_db()


def get_or_create_benchmark_user(db: Session) -> User:
    """The eval harness runs entirely below the auth/HTTP layer, so this is a plain
    ORM row, not a real registration — no password or JWT is ever needed here."""
    user = db.query(User).filter(User.email == BENCHMARK_USER_EMAIL).first()
    if user:
        return user
    user = User(
        email=BENCHMARK_USER_EMAIL,
        hashed_password=None,
        full_name="Benchmark Harness",
        role="individual",
        is_active=True,
        email_verified=True,
        accepted_disclaimer_at=datetime.utcnow(),
        terms_version=settings.TERMS_VERSION,
        privacy_version=settings.PRIVACY_VERSION,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_benchmark_documents(db: Session, user: User) -> None:
    """Remove any documents left over from a previous run via the real delete path,
    so each run starts from a clean, deterministic ingestion state."""
    for doc in document_service.list_documents(db, user):
        document_service.delete_document(db, user, doc.id)
        rag_service.invalidate_rag(doc.id)


async def ingest_fixture_documents(
    db: Session, user: User, documents_dir: Path
) -> dict[str, Document]:
    """
    Upload + ingest every fixture document through the production pipeline
    (validation, chunking, embedding, FAISS index build) exactly as a real user
    upload would, then block until ingestion completes (``run_ingestion_job`` is
    synchronous when called directly, unlike the HTTP route's ``BackgroundTasks``
    invocation of it).

    Returns ``{logical_document_id: Document row}`` where ``logical_document_id``
    is the fixture file's stem (e.g. ``"nda_mutual_001"``), matching each benchmark
    sample's ``source_document.document_id``.
    """
    mapping: dict[str, Document] = {}
    for file_path in sorted(documents_dir.glob("*.txt")):
        content = file_path.read_bytes()
        upload = UploadFile(file=io.BytesIO(content), filename=file_path.name)
        doc = await document_service.accept_upload(db, user, upload)
        document_service.run_ingestion_job(doc.id)
        db.refresh(doc)
        if doc.status != "READY":
            raise RuntimeError(
                f"Fixture document '{file_path.name}' failed ingestion "
                f"(status={doc.status}): {doc.processing_error}"
            )
        mapping[file_path.stem] = doc
    return mapping


__all__ = [
    "REPO_ROOT",
    "BENCHMARK_DIR",
    "SessionLocal",
    "ensure_environment",
    "get_or_create_benchmark_user",
    "reset_benchmark_documents",
    "ingest_fixture_documents",
    "settings",
]
