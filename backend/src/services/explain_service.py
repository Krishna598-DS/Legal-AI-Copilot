"""Explain My Document — grounded multi-query retrieval + structured LLM output."""

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
from src.llm.explain_prompts import (
    EXPLAIN_RETRIEVAL_QUERIES,
    EXPLAIN_SYSTEM_PROMPT,
    build_explain_human_prompt,
)
from src.llm.formatting import format_docs
from src.logging_config import logger
from src.observability.events import log_event
from src.services import confidence as confidence_service
from src.services import document_service, rag_service
from src.services.explain_grounding import (
    _MISSING,
    format_explanation_for_chat,
    normalize_sections,
    parse_llm_json,
)

settings = get_settings()

DISCLAIMER = (
    "This explanation is Legal Information based solely on retrieved excerpts "
    "from your document. It is not Legal Advice and does not replace a licensed lawyer."
)

# Cap merged unique chunks across all topic queries.
_MAX_CONTEXT_CHUNKS = 16


def _chunk_key(doc) -> tuple:
    page = doc.metadata.get("page_number") or doc.metadata.get("page")
    content_type = doc.metadata.get("content_type", "text")
    return (page, content_type, doc.page_content[:120])


def _retrieve_explain_docs(document: Document, user: User) -> list:
    """Run several topic queries and merge unique chunks."""
    embeddings = rag_service.get_embeddings_model()
    store = load_vector_store(embeddings, persist_path=document.index_path)
    k = max(2, min(settings.RETRIEVAL_K, 4))
    merged: list = []
    seen: set[tuple] = set()
    retrieve_started = time.perf_counter()
    try:
        for query in EXPLAIN_RETRIEVAL_QUERIES:
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
            message="explain retrieval failed",
            user_id=user.id,
            document_id=document.id,
            error_type=type(exc).__name__,
        )
        raise RetrievalError(details={"type": type(exc).__name__}) from exc

    log_event(
        logger,
        "retrieval",
        message="explain chunks retrieved",
        user_id=user.id,
        document_id=document.id,
        chunk_count=len(merged),
        latency_ms=round((time.perf_counter() - retrieve_started) * 1000, 2),
        k=k,
        query_count=len(EXPLAIN_RETRIEVAL_QUERIES),
    )
    return merged


def _empty_sections() -> list[dict[str, Any]]:
    from src.llm.explain_prompts import EXPLAIN_SECTION_SPECS

    return [
        {
            "id": spec["id"],
            "title": spec["title"],
            "content": _MISSING,
            "evidence_found": False,
            "citations": [],
        }
        for spec in EXPLAIN_SECTION_SPECS
    ]


def _persist_explanation(
    db: Session,
    document: Document,
    sections: list[dict[str, Any]],
    sources: list[dict],
    processing_time: float,
) -> ChatMessage:
    user_msg = ChatMessage(
        document_id=document.id,
        role="user",
        content="Explain My Document",
    )
    assistant_msg = ChatMessage(
        document_id=document.id,
        role="assistant",
        content=format_explanation_for_chat(sections),
        question_type="explain",
        processing_time=processing_time,
        sources_json=json.dumps(sources),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


def _structured_confidence(
    sources: list[dict],
    sections: list[dict[str, Any]],
    *,
    chunk_count: int,
) -> confidence_service.ConfidenceResult:
    evidenced = [s for s in sections if s.get("evidence_found")]
    cited: list[int] = []
    for sec in evidenced:
        for c in sec.get("citations") or []:
            if isinstance(c, dict) and c.get("index") is not None:
                cited.append(int(c["index"]))
    answer_text = format_explanation_for_chat(sections)
    return confidence_service.estimate_for_structured(
        sources=sources,
        items_with_evidence=len(evidenced),
        total_items=len(sections),
        answer_text=answer_text,
        cited_indices=cited,
        chunk_count=chunk_count,
        target_k=max(3, min(settings.RETRIEVAL_K, 4)),
    )


def _apply_structured_policy(
    sections: list[dict[str, Any]],
    disclaimer: str,
    conf: confidence_service.ConfidenceResult,
) -> tuple[list[dict[str, Any]], str]:
    if conf.confidence_level == "High":
        return sections, disclaimer
    if conf.confidence_level == "Medium":
        note = conf.recommendation
        merged = f"{disclaimer} {note}".strip() if note else disclaimer
        return sections, merged
    # Low: do not present claims confidently — explain why + consult a professional.
    from src.safety.confidence_messaging import build_low_confidence_message

    return _empty_sections(), (
        f"{build_low_confidence_message(conf.factors)} {disclaimer}"
    ).strip()


def explain_document(db: Session, user: User, document_id: str) -> dict:
    """
    Automatically explain a ready document in structured plain language.

    Every section is grounded in retrieved context; missing evidence is explicit.
    """
    start = time.time()
    document = document_service.require_ready_document(db, user, document_id)
    docs = _retrieve_explain_docs(document, user)
    sources = rag_service._sources_from_docs(document, docs)

    if not docs:
        sections = _empty_sections()
        conf = confidence_service.ConfidenceResult(
            confidence_score=0.0,
            confidence_level="Low",
            recommendation=confidence_service.LOW_RECOMMENDATION,
            factors={
                "retrieval_score": 0.0,
                "supporting_chunks": 0.0,
                "citation_coverage": 0.0,
                "answer_grounding": 0.0,
            },
        )
        disclaimer = (
            f"{confidence_service.LOW_ABSTENTION} {DISCLAIMER}"
        ).strip()
        processing_time = round(time.time() - start, 2)
        msg = _persist_explanation(
            db, document, sections, sources, processing_time
        )
        return {
            "document_id": document.id,
            "filename": document.original_filename,
            "sections": sections,
            "sources": sources,
            "processing_time": processing_time,
            "message_id": msg.id,
            "disclaimer": disclaimer,
            **rag_service._confidence_payload(conf),
        }

    context = format_docs(docs)
    prompt = build_explain_human_prompt(document.original_filename, context)
    llm = rag_service.get_llm()

    llm_started = time.perf_counter()
    log_event(
        logger,
        "llm_request",
        message="explain llm invoke started",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type="explain",
    )
    try:
        raw = llm.invoke(
            [
                SystemMessage(content=EXPLAIN_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        ).content
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="explain llm invoke failed",
            user_id=user.id,
            document_id=document.id,
            model=settings.LLM_MODEL,
            error_type=type(exc).__name__,
        )
        raise rag_service._map_llm_exception(exc) from exc

    log_event(
        logger,
        "llm_request",
        message="explain llm invoke completed",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type="explain",
        latency_ms=round((time.perf_counter() - llm_started) * 1000, 2),
    )

    parsed = parse_llm_json(raw if isinstance(raw, str) else str(raw))
    sections = normalize_sections(parsed, sources)
    from src.safety.guardrails import scrub_structured_items

    scrub_codes = scrub_structured_items(sections, text_keys=("content",))
    if scrub_codes:
        log_event(
            logger,
            "safety_violation",
            level=logging.WARNING,
            message="explain sections sanitized",
            user_id=user.id,
            document_id=document.id,
            violation_codes=scrub_codes,
        )
    conf = _structured_confidence(sources, sections, chunk_count=len(docs))
    sections, disclaimer = _apply_structured_policy(sections, DISCLAIMER, conf)
    processing_time = round(time.time() - start, 2)
    assistant_msg = _persist_explanation(
        db, document, sections, sources, processing_time
    )

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "sections": sections,
        "sources": sources,
        "processing_time": processing_time,
        "message_id": assistant_msg.id,
        "disclaimer": disclaimer,
        **rag_service._confidence_payload(conf),
    }


# Re-export names used by unit tests / summary compatibility.
_normalize_sections = normalize_sections
_parse_llm_json = parse_llm_json
