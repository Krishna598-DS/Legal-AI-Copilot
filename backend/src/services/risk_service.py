"""AI legal risk highlighting — grounded multi-query retrieval + structured LLM."""

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
from src.llm.formatting import format_docs
from src.llm.risk_prompts import (
    RISK_RETRIEVAL_QUERIES,
    RISK_SPECS,
    RISK_SYSTEM_PROMPT,
    build_risk_human_prompt,
)
from src.logging_config import logger
from src.observability.events import log_event
from src.services import confidence as confidence_service
from src.services import document_service, rag_service
from src.services.explain_grounding import parse_llm_json
from src.services.risk_grounding import (
    _NO_EVIDENCE,
    format_risks_for_chat,
    normalize_risks,
)

settings = get_settings()

DISCLAIMER = (
    "These risk highlights are Legal Information based solely on retrieved excerpts "
    "from your document. They are not Legal Advice and do not replace a licensed lawyer."
)

_MAX_CONTEXT_CHUNKS = 16


def _chunk_key(doc) -> tuple:
    page = doc.metadata.get("page_number") or doc.metadata.get("page")
    content_type = doc.metadata.get("content_type", "text")
    return (page, content_type, doc.page_content[:120])


def _retrieve_risk_docs(document: Document, user: User) -> list:
    embeddings = rag_service.get_embeddings_model()
    store = load_vector_store(embeddings, persist_path=document.index_path)
    k = max(2, min(settings.RETRIEVAL_K, 4))
    merged: list = []
    seen: set[tuple] = set()
    retrieve_started = time.perf_counter()
    try:
        for query in RISK_RETRIEVAL_QUERIES:
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
            message="risk retrieval failed",
            user_id=user.id,
            document_id=document.id,
            error_type=type(exc).__name__,
        )
        raise RetrievalError(details={"type": type(exc).__name__}) from exc

    log_event(
        logger,
        "retrieval",
        message="risk chunks retrieved",
        user_id=user.id,
        document_id=document.id,
        chunk_count=len(merged),
        latency_ms=round((time.perf_counter() - retrieve_started) * 1000, 2),
        k=k,
        query_count=len(RISK_RETRIEVAL_QUERIES),
    )
    return merged


def _empty_risks() -> list[dict[str, Any]]:
    return [
        {
            "id": spec["id"],
            "title": spec["title"],
            "explanation": _NO_EVIDENCE,
            "severity": None,
            "evidence_found": False,
            "citations": [],
        }
        for spec in RISK_SPECS
    ]


def _persist_risks(
    db: Session,
    document: Document,
    risks: list[dict[str, Any]],
    sources: list[dict],
    processing_time: float,
) -> ChatMessage:
    user_msg = ChatMessage(
        document_id=document.id,
        role="user",
        content="Highlight legal risks",
    )
    assistant_msg = ChatMessage(
        document_id=document.id,
        role="assistant",
        content=format_risks_for_chat(risks),
        question_type="risks",
        processing_time=processing_time,
        sources_json=json.dumps(sources),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


def _risk_confidence(
    sources: list[dict],
    risks: list[dict[str, Any]],
    *,
    chunk_count: int,
) -> confidence_service.ConfidenceResult:
    evidenced = [r for r in risks if r.get("evidence_found")]
    cited: list[int] = []
    for risk in evidenced:
        for c in risk.get("citations") or []:
            if isinstance(c, dict) and c.get("index") is not None:
                cited.append(int(c["index"]))
    return confidence_service.estimate_for_structured(
        sources=sources,
        items_with_evidence=len(evidenced),
        total_items=len(risks),
        answer_text=format_risks_for_chat(risks),
        cited_indices=cited,
        chunk_count=chunk_count,
        target_k=max(3, min(settings.RETRIEVAL_K, 4)),
    )


def _apply_risk_policy(
    risks: list[dict[str, Any]],
    disclaimer: str,
    conf: confidence_service.ConfidenceResult,
) -> tuple[list[dict[str, Any]], str, int]:
    if conf.confidence_level == "High":
        flagged = sum(1 for r in risks if r.get("evidence_found"))
        return risks, disclaimer, flagged
    if conf.confidence_level == "Medium":
        note = conf.recommendation
        merged = f"{disclaimer} {note}".strip() if note else disclaimer
        flagged = sum(1 for r in risks if r.get("evidence_found"))
        return risks, merged, flagged
    from src.safety.confidence_messaging import build_low_confidence_message

    empty = _empty_risks()
    return (
        empty,
        f"{build_low_confidence_message(conf.factors)} {disclaimer}".strip(),
        0,
    )


def analyze_document_risks(db: Session, user: User, document_id: str) -> dict:
    """
    Highlight common legal risks grounded in retrieved context.

    Unsupported checklist items return "No evidence found".
    """
    start = time.time()
    document = document_service.require_ready_document(db, user, document_id)
    docs = _retrieve_risk_docs(document, user)
    sources = rag_service._sources_from_docs(document, docs)

    if not docs:
        risks = _empty_risks()
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
        msg = _persist_risks(db, document, risks, sources, processing_time)
        return {
            "document_id": document.id,
            "filename": document.original_filename,
            "risks": risks,
            "sources": sources,
            "processing_time": processing_time,
            "message_id": msg.id,
            "disclaimer": disclaimer,
            "flagged_count": 0,
            **rag_service._confidence_payload(conf),
        }

    context = format_docs(docs)
    prompt = build_risk_human_prompt(document.original_filename, context)
    llm = rag_service.get_llm()

    llm_started = time.perf_counter()
    log_event(
        logger,
        "llm_request",
        message="risk llm invoke started",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type="risks",
    )
    try:
        raw = llm.invoke(
            [
                SystemMessage(content=RISK_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        ).content
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="risk llm invoke failed",
            user_id=user.id,
            document_id=document.id,
            model=settings.LLM_MODEL,
            error_type=type(exc).__name__,
        )
        raise rag_service._map_llm_exception(exc) from exc

    log_event(
        logger,
        "llm_request",
        message="risk llm invoke completed",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type="risks",
        latency_ms=round((time.perf_counter() - llm_started) * 1000, 2),
    )

    parsed = parse_llm_json(raw if isinstance(raw, str) else str(raw))
    risks = normalize_risks(parsed, sources)
    from src.safety.guardrails import scrub_structured_items

    scrub_codes = scrub_structured_items(
        risks,
        text_keys=("explanation",),
        missing_text="No evidence found",
    )
    if scrub_codes:
        log_event(
            logger,
            "safety_violation",
            level=logging.WARNING,
            message="risk explanations sanitized",
            user_id=user.id,
            document_id=document.id,
            violation_codes=scrub_codes,
        )
    conf = _risk_confidence(sources, risks, chunk_count=len(docs))
    risks, disclaimer, flagged_count = _apply_risk_policy(risks, DISCLAIMER, conf)
    processing_time = round(time.time() - start, 2)
    assistant_msg = _persist_risks(
        db, document, risks, sources, processing_time
    )

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "risks": risks,
        "sources": sources,
        "processing_time": processing_time,
        "message_id": assistant_msg.id,
        "disclaimer": disclaimer,
        "flagged_count": flagged_count,
        **rag_service._confidence_payload(conf),
    }
