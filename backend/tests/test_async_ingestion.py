"""Async document ingestion via FastAPI BackgroundTasks."""

from __future__ import annotations

import asyncio
import os
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile

_tmp = tempfile.mkdtemp()
_upload = os.path.join(_tmp, "uploads")
_index = os.path.join(_tmp, "indexes")
os.makedirs(_upload, exist_ok=True)
os.makedirs(_index, exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test_ingest.db"
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
os.environ["ENABLE_UPLOAD_SCAN"] = "false"

from src.config import clear_settings_cache

clear_settings_cache()

from src.api.main import app
from src.db.database import SessionLocal, init_db
from src.db.models import Document, User
from src.errors import ValidationAppError
from src.services import document_service, document_status

init_db()


def _register(client: TestClient, email: str) -> dict:
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "testpass123",
            "full_name": "Ingest",
            "role": "individual",
            "accept_disclaimer": True,
        },
    )
    if r.status_code not in (200, 201):
        r = client.post(
            "/auth/login", json={"email": email, "password": "testpass123"}
        )
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_status_helpers():
    assert document_status.is_ready("READY")
    assert document_status.is_ready("ready")
    assert not document_status.is_ready("PROCESSING")
    assert document_status.normalize_status("uploading") == "UPLOADING"
    assert document_status.is_terminal("FAILED")


def test_accept_upload_returns_immediately_without_embedding():
    """Upload endpoint queues work; response is UPLOADING before job runs."""
    content = b"Hello async ingestion contract text.\n"
    captured: dict = {}

    def capture_task(self, fn, *args, **kwargs):
        captured["fn"] = fn
        captured["args"] = args

    with patch.object(BackgroundTasks, "add_task", capture_task):
        with TestClient(app) as client:
            headers = _register(client, "ingest-immediate@example.com")
            resp = client.post(
                "/documents/upload",
                headers=headers,
                files={"file": ("clause.txt", content, "text/plain")},
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "Processing started" in body["message"]
    doc = body["document"]
    assert doc["status"] == document_status.UPLOADING
    assert doc["num_chunks"] == 0
    assert doc["processing_error"] is None
    assert captured.get("fn") is document_service.run_ingestion_job
    assert captured.get("args") == (doc["id"],)

    db = SessionLocal()
    try:
        row = db.get(Document, doc["id"])
        assert row is not None
        assert os.path.isfile(row.file_path)
        assert row.status == document_status.UPLOADING
    finally:
        db.close()


def test_accept_upload_service_creates_uploading_row():
    db = SessionLocal()
    try:
        user = User(
            email="svc-ingest@example.com",
            hashed_password="x",
            email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        upload = UploadFile(
            file=BytesIO(b"Service level upload body\n"),
            filename="note.txt",
            headers=Headers({"content-type": "text/plain"}),
        )
        doc = asyncio.run(document_service.accept_upload(db, user, upload))
        assert doc.status == document_status.UPLOADING
        assert doc.num_chunks == 0
        assert os.path.isfile(doc.file_path)
    finally:
        db.close()


def test_run_ingestion_job_success():
    db = SessionLocal()
    try:
        user = User(
            email="job-ok@example.com",
            hashed_password="x",
            email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        doc_id = "11111111-1111-1111-1111-111111111111"
        upload_dir = os.path.join(_upload, user.id)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{doc_id}_note.txt")
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write("Payment is due in thirty days.\n")
        index_path = os.path.join(_index, user.id, doc_id)

        doc = Document(
            id=doc_id,
            user_id=user.id,
            filename=f"{doc_id}_note.txt",
            original_filename="note.txt",
            file_path=file_path,
            index_path=index_path,
            status=document_status.UPLOADING,
            file_size_bytes=32,
        )
        db.add(doc)
        db.commit()
    finally:
        db.close()

    fake_chunks = [MagicMock()]
    with (
        patch(
            "src.services.document_service.load_document",
            return_value=[
                MagicMock(
                    metadata={"page_count": 1, "has_tables": False},
                    page_content="Payment is due",
                )
            ],
        ),
        patch(
            "src.services.document_service.chunk_documents",
            return_value=fake_chunks,
        ),
        patch(
            "src.services.document_service.create_embeddings",
            return_value=MagicMock(),
        ),
        patch(
            "src.services.document_service.create_vector_store",
            return_value=MagicMock(),
        ) as mock_vs,
    ):
        document_service.run_ingestion_job(doc_id)

    db = SessionLocal()
    try:
        row = db.get(Document, doc_id)
        assert row.status == document_status.READY
        assert row.num_chunks == 1
        assert row.page_count == 1
        assert row.processing_error is None
        mock_vs.assert_called_once()
    finally:
        db.close()


def test_run_ingestion_job_failure_stores_error():
    db = SessionLocal()
    try:
        user = User(
            email="job-fail@example.com",
            hashed_password="x",
            email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        doc_id = "22222222-2222-2222-2222-222222222222"
        upload_dir = os.path.join(_upload, user.id)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{doc_id}_bad.txt")
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write("will fail\n")
        index_path = os.path.join(_index, user.id, doc_id)

        doc = Document(
            id=doc_id,
            user_id=user.id,
            filename=f"{doc_id}_bad.txt",
            original_filename="bad.txt",
            file_path=file_path,
            index_path=index_path,
            status=document_status.UPLOADING,
            file_size_bytes=10,
        )
        db.add(doc)
        db.commit()
    finally:
        db.close()

    with patch(
        "src.services.document_service.load_document",
        side_effect=RuntimeError("parse exploded"),
    ):
        document_service.run_ingestion_job(doc_id)

    db = SessionLocal()
    try:
        row = db.get(Document, doc_id)
        assert row.status == document_status.FAILED
        assert row.processing_error is not None
        assert "parse exploded" in row.processing_error
        assert "RuntimeError" in row.processing_error
    finally:
        db.close()


def test_require_ready_document_blocks_processing():
    db = SessionLocal()
    try:
        user = User(
            email="not-ready@example.com",
            hashed_password="x",
            email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        doc = Document(
            id="33333333-3333-3333-3333-333333333333",
            user_id=user.id,
            filename="x.txt",
            original_filename="x.txt",
            file_path=os.path.join(_upload, "x.txt"),
            index_path=os.path.join(_index, "x"),
            status=document_status.PROCESSING,
        )
        db.add(doc)
        db.commit()

        with pytest.raises(ValidationAppError) as ei:
            document_service.require_ready_document(db, user, doc.id)
        assert ei.value.code == "DOCUMENT_NOT_READY"
    finally:
        db.close()


def test_require_ready_document_surfaces_failure():
    db = SessionLocal()
    try:
        user = User(
            email="failed-doc@example.com",
            hashed_password="x",
            email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        doc = Document(
            id="44444444-4444-4444-4444-444444444444",
            user_id=user.id,
            filename="y.txt",
            original_filename="y.txt",
            file_path=os.path.join(_upload, "y.txt"),
            index_path=os.path.join(_index, "y"),
            status=document_status.FAILED,
            processing_error="RuntimeError: boom",
        )
        db.add(doc)
        db.commit()

        with pytest.raises(ValidationAppError) as ei:
            document_service.require_ready_document(db, user, doc.id)
        assert ei.value.code == "DOCUMENT_PROCESSING_FAILED"
        assert ei.value.details.get("processing_error") == "RuntimeError: boom"
    finally:
        db.close()
