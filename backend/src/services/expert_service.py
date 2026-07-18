"""Expert recommendation engine — category only, never specific professionals."""

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
from src.llm.expert_prompts import (
    EXPERT_RETRIEVAL_QUERIES,
    EXPERT_SYSTEM_PROMPT,
    build_expert_human_prompt,
)
from src.llm.formatting import format_docs
from src.logging_config import logger
from src.observability.events import log_event
from src.services import document_service, rag_service
from src.services.explain_grounding import parse_llm_json
from src.services.expert_grounding import (
    detect_risk_signals,
    normalize_recommendation,
    score_categories,
)

settings = get_settings()

DISCLAIMER = (
    "This recommends an expert category only — not a specific professional. "
    "It is not a referral and not legal advice."
)

_MAX_CONTEXT_CHUNKS = 12
_MAX_QUESTIONS = 12


def _chunk_key(doc) -> tuple:
    page = doc.metadata.get("page_number") or doc.metadata.get("page")
    content_type = doc.metadata.get("content_type", "text")
    return (page, content_type, doc.page_content[:120])


def _retrieve_expert_docs(document: Document, user: User) -> list:
    embeddings = rag_service.get_embeddings_model()
    store = load_vector_store(embeddings, persist_path=document.index_path)
    k = max(2, min(settings.RETRIEVAL_K, 4))
    merged: list = []
    seen: set[tuple] = set()
    retrieve_started = time.perf_counter()
    try:
        for query in EXPERT_RETRIEVAL_QUERIES:
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
            message="expert retrieval failed",
            user_id=user.id,
            document_id=document.id,
            error_type=type(exc).__name__,
        )
        raise RetrievalError(details={"type": type(exc).__name__}) from exc

    log_event(
        logger,
        "retrieval",
        message="expert chunks retrieved",
        user_id=user.id,
        document_id=document.id,
        chunk_count=len(merged),
        latency_ms=round((time.perf_counter() - retrieve_started) * 1000, 2),
        k=k,
        query_count=len(EXPERT_RETRIEVAL_QUERIES),
    )
    return merged


def _collect_user_questions(
    db: Session, user: User, document_id: str
) -> list[str]:
    messages = document_service.get_chat_history(db, user, document_id)
    questions: list[str] = []
    for msg in messages:
        if msg.role != "user":
            continue
        content = (msg.content or "").strip()
        if not content:
            continue
        # Skip system-triggered prompts that are not real user questions.
        if content in {"Explain My Document", "Highlight legal risks"}:
            continue
        questions.append(content)
    return questions[-_MAX_QUESTIONS:]


def _risks_from_chat_history(
    db: Session, user: User, document_id: str
) -> list[str]:
    """Pull risk titles previously persisted from a risk scan, if any."""
    messages = document_service.get_chat_history(db, user, document_id)
    titles: list[str] = []
    for msg in reversed(messages):
        if msg.role != "assistant" or msg.question_type != "risks":
            continue
        content = msg.content or ""
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("Citations:") or line == "Legal Risk Highlights":
                continue
            # Lines look like: "Arbitration clause [High]"
            if line.endswith("]") and "[" in line:
                title = line.rsplit("[", 1)[0].strip()
                if title and title not in titles:
                    titles.append(title)
        if titles:
            break
    return titles


def _persist_recommendation(
    db: Session,
    document: Document,
    category: str,
    reason: str,
    sources: list[dict],
    processing_time: float,
) -> ChatMessage:
    user_msg = ChatMessage(
        document_id=document.id,
        role="user",
        content="Recommend an expert category",
    )
    assistant_msg = ChatMessage(
        document_id=document.id,
        role="assistant",
        content=(
            f"Recommended Expert:\n{category}\n\n"
            f"Reason:\n{reason}\n\n"
            f"{DISCLAIMER}"
        ),
        question_type="expert",
        processing_time=processing_time,
        sources_json=json.dumps(sources),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


def recommend_expert(db: Session, user: User, document_id: str) -> dict[str, Any]:
    """
    Recommend the single most relevant expert category for a document.

    Uses retrieved document excerpts, recent user questions, and detected risks.
    Never returns a specific named professional.
    """
    start = time.time()
    document = document_service.require_ready_document(db, user, document_id)
    docs = _retrieve_expert_docs(document, user)
    sources = rag_service._sources_from_docs(document, docs)
    questions = _collect_user_questions(db, user, document.id)
    context_text = "\n".join(d.page_content for d in docs)
    filename_bit = document.original_filename or ""
    detected_risks = detect_risk_signals(context_text)
    for title in _risks_from_chat_history(db, user, document.id):
        if title not in detected_risks:
            detected_risks.append(title)

    fallback_blob = " ".join(
        [filename_bit, context_text, " ".join(questions), " ".join(detected_risks)]
    )

    if not docs and not questions:
        normalized = normalize_recommendation(
            {},
            fallback_text=filename_bit or "civil dispute",
        )
        normalized["reason"] = (
            "There was not enough retrieved document content or question history "
            f"to specialize further, so a {normalized['category']} is suggested "
            "as the most general fit. Upload a clearer document or ask a question "
            "for a sharper recommendation."
        )
        processing_time = round(time.time() - start, 2)
        msg = _persist_recommendation(
            db,
            document,
            normalized["category"],
            normalized["reason"],
            sources,
            processing_time,
        )
        return {
            "document_id": document.id,
            "filename": document.original_filename,
            "category": normalized["category"],
            "reason": normalized["reason"],
            "based_on": {
                "document": False,
                "questions": False,
                "risks": False,
            },
            "detected_risks": detected_risks,
            "questions_considered": questions,
            "sources": sources,
            "processing_time": processing_time,
            "message_id": msg.id,
            "disclaimer": DISCLAIMER,
            "category_scores": score_categories(fallback_blob),
        }

    context = format_docs(docs) if docs else "(no excerpts retrieved)"
    prompt = build_expert_human_prompt(
        filename=document.original_filename,
        context=context,
        questions=questions,
        detected_risks=detected_risks,
    )
    llm = rag_service.get_llm()

    llm_started = time.perf_counter()
    log_event(
        logger,
        "llm_request",
        message="expert recommend llm invoke started",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type="expert",
    )
    try:
        raw = llm.invoke(
            [
                SystemMessage(content=EXPERT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        ).content
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="expert recommend llm invoke failed",
            user_id=user.id,
            document_id=document.id,
            model=settings.LLM_MODEL,
            error_type=type(exc).__name__,
        )
        # Deterministic fallback — still never invent a person.
        normalized = normalize_recommendation({}, fallback_text=fallback_blob)
        normalized["reason"] = (
            f"{normalized['reason']} (Generated from document/question/risk "
            "keyword signals after the AI service was unavailable.)"
        )
        processing_time = round(time.time() - start, 2)
        msg = _persist_recommendation(
            db,
            document,
            normalized["category"],
            normalized["reason"],
            sources,
            processing_time,
        )
        return {
            "document_id": document.id,
            "filename": document.original_filename,
            "category": normalized["category"],
            "reason": normalized["reason"],
            "based_on": {
                "document": bool(docs),
                "questions": bool(questions),
                "risks": bool(detected_risks),
            },
            "detected_risks": detected_risks,
            "questions_considered": questions,
            "sources": sources,
            "processing_time": processing_time,
            "message_id": msg.id,
            "disclaimer": DISCLAIMER,
            "category_scores": score_categories(fallback_blob),
        }

    log_event(
        logger,
        "llm_request",
        message="expert recommend llm invoke completed",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type="expert",
        latency_ms=round((time.perf_counter() - llm_started) * 1000, 2),
    )

    parsed = parse_llm_json(raw if isinstance(raw, str) else str(raw))
    normalized = normalize_recommendation(parsed, fallback_text=fallback_blob)
    # Ensure based_on reflects actual inputs when the model omits flags.
    based_on = {
        "document": bool(docs) and bool(normalized["based_on"].get("document", True)),
        "questions": bool(questions),
        "risks": bool(detected_risks),
    }
    if questions:
        based_on["questions"] = True
    if detected_risks:
        based_on["risks"] = True
    if docs:
        based_on["document"] = True

    processing_time = round(time.time() - start, 2)
    assistant_msg = _persist_recommendation(
        db,
        document,
        normalized["category"],
        normalized["reason"],
        sources,
        processing_time,
    )

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "category": normalized["category"],
        "reason": normalized["reason"],
        "based_on": based_on,
        "detected_risks": detected_risks,
        "questions_considered": questions,
        "sources": sources,
        "processing_time": processing_time,
        "message_id": assistant_msg.id,
        "disclaimer": DISCLAIMER,
        "category_scores": score_categories(fallback_blob),
    }
