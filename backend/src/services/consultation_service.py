"""Prepare for Consultation — grounded briefing + PDF export."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.models import ChatMessage, Document, User
from src.errors import RetrievalError
from src.ingestion.vector_store import load_vector_store
from src.llm.consultation_prompts import (
    CONSULTATION_RETRIEVAL_QUERIES,
    CONSULTATION_SECTION_SPECS,
    CONSULTATION_SYSTEM_PROMPT,
    build_consultation_human_prompt,
)
from src.llm.formatting import format_docs
from src.logging_config import logger
from src.observability.events import log_event
from src.services import document_service, rag_service
from src.services.consultation_grounding import (
    _MISSING,
    format_consultation_for_chat,
    normalize_consultation_sections,
)
from src.services.consultation_pdf import DISCLAIMER as PDF_DISCLAIMER
from src.services.consultation_pdf import build_consultation_pdf
from src.services.explain_grounding import parse_llm_json

settings = get_settings()

DISCLAIMER = (
    "This briefing is Legal Information summarizing retrieved excerpts to help you "
    "prepare for a consultation. It is not Legal Advice and does not replace a "
    "licensed lawyer."
)

_MAX_CONTEXT_CHUNKS = 16
# Short-lived cache so PDF export can reuse the last briefing without a second LLM call.
_prep_cache: dict[str, dict[str, Any]] = {}


def _cache_key(user_id: str, document_id: str) -> str:
    return f"{user_id}:{document_id}"


def _chunk_key(doc) -> tuple:
    page = doc.metadata.get("page_number") or doc.metadata.get("page")
    content_type = doc.metadata.get("content_type", "text")
    return (page, content_type, doc.page_content[:120])


def _retrieve_consultation_docs(document: Document, user: User) -> list:
    embeddings = rag_service.get_embeddings_model()
    store = load_vector_store(embeddings, persist_path=document.index_path)
    k = max(2, min(settings.RETRIEVAL_K, 4))
    merged: list = []
    seen: set[tuple] = set()
    retrieve_started = time.perf_counter()
    try:
        for query in CONSULTATION_RETRIEVAL_QUERIES:
            hits = store.similarity_search_with_score(query, k=k)
            for doc, distance in hits:
                key = _chunk_key(doc)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    doc.metadata["retrieval_distance"] = float(distance)
                except (TypeError, ValueError):
                    pass
                merged.append(doc)
                if len(merged) >= _MAX_CONTEXT_CHUNKS:
                    break
            if len(merged) >= _MAX_CONTEXT_CHUNKS:
                break
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="consultation retrieval failed",
            user_id=user.id,
            document_id=document.id,
            error_type=type(exc).__name__,
        )
        raise RetrievalError(details={"type": type(exc).__name__}) from exc

    log_event(
        logger,
        "retrieval",
        message="consultation chunks retrieved",
        user_id=user.id,
        document_id=document.id,
        chunk_count=len(merged),
        latency_ms=round((time.perf_counter() - retrieve_started) * 1000, 2),
        k=k,
        query_count=len(CONSULTATION_RETRIEVAL_QUERIES),
    )
    return merged


def _empty_sections(uploaded_filename: str | None = None) -> list[dict[str, Any]]:
    sections = [
        {
            "id": spec["id"],
            "title": spec["title"],
            "content": _MISSING,
            "items": [],
            "evidence_found": False,
            "citations": [],
        }
        for spec in CONSULTATION_SECTION_SPECS
    ]
    if uploaded_filename:
        for sec in sections:
            if sec["id"] == "documents_to_carry":
                sec["content"] = (
                    f"Uploaded document: {uploaded_filename}. "
                    "No retrieved excerpts were available to identify additional attachments."
                )
                sec["items"] = [f"Uploaded document: {uploaded_filename}"]
                sec["evidence_found"] = False
    return sections


def _persist_prep(
    db: Session,
    document: Document,
    sections: list[dict[str, Any]],
    sources: list[dict],
    processing_time: float,
) -> ChatMessage:
    user_msg = ChatMessage(
        document_id=document.id,
        role="user",
        content="Prepare for Consultation",
    )
    assistant_msg = ChatMessage(
        document_id=document.id,
        role="assistant",
        content=format_consultation_for_chat(sections),
        question_type="consultation",
        processing_time=processing_time,
        sources_json=json.dumps(sources),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


def prepare_consultation(
    db: Session, user: User, document_id: str
) -> dict[str, Any]:
    """
    Generate a grounded consultation prep briefing for a ready document.
    """
    start = time.time()
    document = document_service.require_ready_document(db, user, document_id)
    docs = _retrieve_consultation_docs(document, user)
    sources = rag_service._sources_from_docs(document, docs)

    if not docs:
        sections = _empty_sections(document.original_filename)
        processing_time = round(time.time() - start, 2)
        msg = _persist_prep(db, document, sections, sources, processing_time)
        payload = {
            "document_id": document.id,
            "filename": document.original_filename,
            "sections": sections,
            "sources": sources,
            "processing_time": processing_time,
            "message_id": msg.id,
            "disclaimer": DISCLAIMER,
            "export_filename": _safe_export_name(document.original_filename),
        }
        _prep_cache[_cache_key(user.id, document.id)] = payload
        return payload

    context = format_docs(docs)
    prompt = build_consultation_human_prompt(
        document.original_filename, context
    )
    llm = rag_service.get_llm()

    llm_started = time.perf_counter()
    log_event(
        logger,
        "llm_request",
        message="consultation llm invoke started",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type="consultation",
    )
    try:
        raw = llm.invoke(
            [
                SystemMessage(content=CONSULTATION_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        ).content
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="consultation llm invoke failed",
            user_id=user.id,
            document_id=document.id,
            model=settings.LLM_MODEL,
            error_type=type(exc).__name__,
        )
        raise rag_service._map_llm_exception(exc) from exc

    log_event(
        logger,
        "llm_request",
        message="consultation llm invoke completed",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type="consultation",
        latency_ms=round((time.perf_counter() - llm_started) * 1000, 2),
    )

    parsed = parse_llm_json(raw if isinstance(raw, str) else str(raw))
    sections = normalize_consultation_sections(
        parsed,
        sources,
        uploaded_filename=document.original_filename,
    )
    from src.safety.guardrails import scrub_structured_items

    scrub_codes = scrub_structured_items(sections, text_keys=("content",))
    if scrub_codes:
        log_event(
            logger,
            "safety_violation",
            level=logging.WARNING,
            message="consultation sections sanitized",
            user_id=user.id,
            document_id=document.id,
            violation_codes=scrub_codes,
        )
    processing_time = round(time.time() - start, 2)
    assistant_msg = _persist_prep(
        db, document, sections, sources, processing_time
    )

    payload = {
        "document_id": document.id,
        "filename": document.original_filename,
        "sections": sections,
        "sources": sources,
        "processing_time": processing_time,
        "message_id": assistant_msg.id,
        "disclaimer": DISCLAIMER,
        "export_filename": _safe_export_name(document.original_filename),
    }
    _prep_cache[_cache_key(user.id, document.id)] = payload
    return payload


def prepare_consultation_pdf(
    db: Session,
    user: User,
    document_id: str,
    *,
    use_cache: bool = True,
) -> tuple[bytes, str, dict[str, Any]]:
    """
    Render the consultation briefing as a PDF.

    Reuses the last in-memory prep for this user/document when available
    so Export PDF does not require a second LLM call.
    """
    key = _cache_key(user.id, document_id)
    prep = _prep_cache.get(key) if use_cache else None
    if prep is None:
        prep = prepare_consultation(db, user, document_id)
    pdf_bytes = build_consultation_pdf(
        filename=prep["filename"],
        sections=prep["sections"],
        disclaimer=f"{prep['disclaimer']} {PDF_DISCLAIMER}",
    )
    return pdf_bytes, prep["export_filename"], prep


def _safe_export_name(original: str | None) -> str:
    base = (original or "document").rsplit(".", 1)[0]
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in base)
    cleaned = cleaned.strip("_") or "document"
    return f"{cleaned}_consultation_prep.pdf"
