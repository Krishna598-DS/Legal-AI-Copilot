"""Document ingestion and lifecycle service (per-user isolation)."""

from __future__ import annotations

import logging
import os
import shutil
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.database import SessionLocal
from src.db.models import ChatMessage, Document, User
from src.errors import DocumentNotFoundError, ValidationAppError
from src.ingestion.document_loader import load_document
from src.ingestion.embeddings import create_embeddings
from src.ingestion.text_chunker import chunk_documents
from src.ingestion.vector_store import create_vector_store, delete_vector_store
from src.logging_config import logger
from src.observability.events import log_event
from src.services import document_status
from src.services.scan_service import scan_bytes
from src.validation.file_upload import ensure_path_within, validate_upload

settings = get_settings()


def _user_upload_dir(user_id: str) -> str:
    path = os.path.join(settings.UPLOAD_DIR, user_id)
    os.makedirs(path, exist_ok=True)
    return path


def _user_index_dir(user_id: str, document_id: str) -> str:
    path = os.path.join(settings.INDEX_DIR, user_id, document_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_user_document(db: Session, user: User, document_id: str) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user.id)
        .first()
    )
    if not doc:
        raise DocumentNotFoundError()
    return doc


def require_ready_document(db: Session, user: User, document_id: str) -> Document:
    """Return document only when ingestion completed successfully."""
    doc = get_user_document(db, user, document_id)
    status = document_status.normalize_status(doc.status)
    if status == document_status.READY:
        return doc
    if status == document_status.FAILED:
        raise ValidationAppError(
            "Document processing failed. Re-upload the file or delete it.",
            code="DOCUMENT_PROCESSING_FAILED",
            details={
                "status": status,
                "processing_error": doc.processing_error,
            },
        )
    raise ValidationAppError(
        "Document is still processing. Try again shortly.",
        code="DOCUMENT_NOT_READY",
        details={"status": status},
    )


async def accept_upload(db: Session, user: User, file: UploadFile) -> Document:
    """
    Validate + persist upload, create DB row, return immediately.

    Heavy work (parse/chunk/embed) runs in ``run_ingestion_job``.
    """
    owned = db.query(Document).filter(Document.user_id == user.id).count()
    if owned >= settings.MAX_DOCUMENTS_PER_USER:
        raise ValidationAppError(
            f"Document limit reached ({settings.MAX_DOCUMENTS_PER_USER}). "
            "Delete a document before uploading another.",
            code="DOCUMENT_LIMIT_REACHED",
            details={"limit": settings.MAX_DOCUMENTS_PER_USER},
        )

    content = await file.read()
    validated = validate_upload(
        filename=file.filename,
        content=content,
        content_type=file.content_type,
    )
    scan_bytes(content, validated.filename)

    document_id = str(uuid.uuid4())
    stored_name = f"{document_id}_{validated.safe_filename}"
    upload_dir = _user_upload_dir(user.id)
    file_path = os.path.join(upload_dir, stored_name)
    ensure_path_within(upload_dir, file_path)

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    index_path = _user_index_dir(user.id, document_id)

    doc = Document(
        id=document_id,
        user_id=user.id,
        filename=stored_name,
        original_filename=validated.filename,
        file_path=file_path,
        index_path=index_path,
        num_chunks=0,
        file_size_bytes=len(content),
        status=document_status.UPLOADING,
        page_count=0,
        has_tables=False,
        processing_error=None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_event(
        logger,
        "upload",
        message="document file saved; ingestion queued",
        user_id=user.id,
        document_id=document_id,
        filename=validated.filename,
        status=doc.status,
    )
    return doc


def run_ingestion_job(document_id: str) -> None:
    """
    Background task: parse → chunk → embed → FAISS → update metadata/status.

    Opens its own DB session (request session is closed after the response).
    """
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if not doc:
            logger.warning("Ingestion job skipped; document missing id=%s", document_id)
            return

        doc.status = document_status.PROCESSING
        doc.processing_error = None
        db.commit()

        log_event(
            logger,
            "upload",
            message="document ingestion started",
            user_id=doc.user_id,
            document_id=doc.id,
            status=doc.status,
        )

        file_path = doc.file_path
        index_path = doc.index_path

        documents = load_document(file_path)
        page_count = (
            int(documents[0].metadata.get("page_count", 1)) if documents else 1
        )
        has_tables = (
            bool(documents[0].metadata.get("has_tables", False)) if documents else False
        )
        chunks = chunk_documents(documents)
        embeddings_model = create_embeddings()
        create_vector_store(chunks, embeddings_model, persist_path=index_path)

        # Re-load in case of concurrent delete
        doc = db.get(Document, document_id)
        if not doc:
            delete_vector_store(index_path)
            return

        doc.num_chunks = len(chunks)
        doc.page_count = page_count
        doc.has_tables = has_tables
        doc.status = document_status.READY
        doc.processing_error = None
        db.commit()

        log_event(
            logger,
            "upload",
            message="document ingestion completed",
            user_id=doc.user_id,
            document_id=doc.id,
            num_chunks=len(chunks),
            page_count=page_count,
            status=doc.status,
        )
    except Exception as exc:
        logger.exception("Document ingestion failed id=%s", document_id)
        try:
            doc = db.get(Document, document_id)
            if doc:
                delete_vector_store(doc.index_path)
                doc.status = document_status.FAILED
                doc.processing_error = _format_processing_error(exc)
                db.commit()
                log_event(
                    logger,
                    "error",
                    level=logging.ERROR,
                    message="document ingestion failed",
                    user_id=doc.user_id,
                    document_id=document_id,
                    status=doc.status,
                    error_type=type(exc).__name__,
                )
        except Exception:
            logger.exception(
                "Failed to persist FAILED status for document id=%s", document_id
            )
    finally:
        db.close()


def _format_processing_error(exc: BaseException) -> str:
    """Store a concise error for the client; avoid huge traces."""
    text = f"{type(exc).__name__}: {exc}"
    return text[:2000]


# Backward-compatible alias used by older callers/tests
async def process_upload(db: Session, user: User, file: UploadFile) -> Document:
    return await accept_upload(db, user, file)


def list_documents(db: Session, user: User) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


def delete_document(db: Session, user: User, document_id: str) -> None:
    doc = get_user_document(db, user, document_id)

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    delete_vector_store(doc.index_path)

    parent = os.path.dirname(doc.index_path)
    if os.path.isdir(parent) and not os.listdir(parent):
        shutil.rmtree(parent, ignore_errors=True)

    db.delete(doc)
    db.commit()
    log_event(
        logger,
        "delete",
        message="document deleted",
        user_id=user.id,
        document_id=document_id,
        filename=doc.original_filename,
    )


def get_chat_history(db: Session, user: User, document_id: str) -> list[ChatMessage]:
    get_user_document(db, user, document_id)
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.document_id == document_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


def clear_chat_history(db: Session, user: User, document_id: str) -> None:
    get_user_document(db, user, document_id)
    db.query(ChatMessage).filter(ChatMessage.document_id == document_id).delete()
    db.commit()


def delete_user_account(db: Session, user: User) -> None:
    """Delete all user data: files, indexes, DB rows."""
    docs = list_documents(db, user)
    for doc in docs:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        delete_vector_store(doc.index_path)

    user_upload = os.path.join(settings.UPLOAD_DIR, user.id)
    user_index = os.path.join(settings.INDEX_DIR, user.id)
    shutil.rmtree(user_upload, ignore_errors=True)
    shutil.rmtree(user_index, ignore_errors=True)

    db.delete(user)
    db.commit()
    logger.info("Account deleted user=%s", user.id)
