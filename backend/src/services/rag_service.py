"""Per-document conversational RAG with citations + streaming."""

from __future__ import annotations

import json
import logging
import time
from collections import OrderedDict
from collections.abc import Iterator
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.models import ChatMessage, Document, User
from src.errors import OpenAIServiceError, RetrievalError
from src.errors.exceptions import AppError
from src.ingestion.embeddings import create_embeddings
from src.ingestion.vector_store import load_vector_store
from src.llm.conversational_chain import ConversationalRAG
from src.llm.prompt_templates import classify_question
from src.logging_config import logger
from src.observability.events import log_event
from src.retrieval.retriever import get_retriever
from src.services import document_service
from src.services import confidence as confidence_service
from src.services.query_embedding_cache import install_query_embedding_cache

settings = get_settings()
_rag_cache: OrderedDict[str, ConversationalRAG] = OrderedDict()


def _map_llm_exception(exc: BaseException) -> AppError:
    """Convert provider/LLM failures into a safe client-facing error."""
    if isinstance(exc, AppError):
        return exc
    err_type = type(exc).__name__
    module = type(exc).__module__ or ""
    if "RateLimit" in err_type:
        return OpenAIServiceError(
            "AI rate limit exceeded. Try again shortly.",
            code="OPENAI_RATE_LIMIT",
            details={"type": err_type},
        )
    if "Auth" in err_type or "Authentication" in err_type:
        return OpenAIServiceError(
            "AI service authentication failed.",
            code="OPENAI_AUTH_ERROR",
            details={"type": err_type},
        )
    if "openai" in module.lower() or "OpenAI" in err_type or "APIError" in err_type:
        return OpenAIServiceError(details={"type": err_type})
    return OpenAIServiceError(details={"type": err_type})


def _cache_get(document_id: str) -> ConversationalRAG | None:
    rag = _rag_cache.get(document_id)
    if rag is not None:
        _rag_cache.move_to_end(document_id)
    return rag


def _cache_put(document_id: str, rag: ConversationalRAG) -> None:
    _rag_cache[document_id] = rag
    _rag_cache.move_to_end(document_id)
    max_size = settings.CACHE_SIZE
    if max_size > 0:
        while len(_rag_cache) > max_size:
            _rag_cache.popitem(last=False)


@lru_cache
def get_embeddings_model():
    embeddings = create_embeddings()
    # Sprint 2A Task 2 (see query_embedding_cache.py): avoids re-embedding the same
    # standalone query twice per question (once for retrieval, once for
    # `_faiss_score_map`'s confidence-scoring lookup). Retrieval behavior/results
    # are unchanged — this only removes a duplicate, deterministic API call.
    install_query_embedding_cache(embeddings)
    return embeddings


@lru_cache
def get_llm():
    if not settings.OPENAI_API_KEY:
        raise OpenAIServiceError(
            "AI service is not configured.",
            code="OPENAI_NOT_CONFIGURED",
        )
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
        max_retries=settings.RETRY_COUNT,
        request_timeout=settings.REQUEST_TIMEOUT,
    )


def _load_history_into_rag(rag: ConversationalRAG, messages: list[ChatMessage]) -> None:
    rag.reset_memory()
    window = settings.CHAT_MEMORY_WINDOW
    recent = messages[-window:] if window > 0 else messages
    for msg in recent:
        if msg.role == "user":
            rag.chat_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            rag.chat_history.append(AIMessage(content=msg.content))


def get_or_create_rag(db: Session, user: User, document: Document) -> ConversationalRAG:
    cached = _cache_get(document.id)
    if cached is not None:
        return cached

    embeddings = get_embeddings_model()
    llm = get_llm()
    vector_store = load_vector_store(embeddings, persist_path=document.index_path)
    retriever = get_retriever(vector_store, k=settings.RETRIEVAL_K)
    rag = ConversationalRAG(
        retriever, llm, memory_window=settings.CHAT_MEMORY_WINDOW
    )

    history = document_service.get_chat_history(db, user, document.id)
    if history:
        _load_history_into_rag(rag, history)

    _cache_put(document.id, rag)
    logger.info("RAG loaded for document=%s", document.id)
    return rag


def invalidate_rag(document_id: str) -> None:
    _rag_cache.pop(document_id, None)


def _sources_from_docs(
    document: Document,
    docs,
    *,
    score_by_key: dict[tuple, float] | None = None,
) -> list[dict]:
    sources = []
    seen = set()
    for i, doc in enumerate(docs, start=1):
        page = doc.metadata.get("page_number") or doc.metadata.get("page")
        content_type = doc.metadata.get("content_type", "text")
        key = (page, content_type, doc.page_content[:80])
        if key in seen:
            continue
        seen.add(key)
        entry = {
            "index": i,
            "filename": document.original_filename,
            "document_id": document.id,
            "page": page,
            "content_type": content_type,
            "snippet": doc.page_content[:240],
            "type": "legal_document",
        }
        # Prefer explicit metadata distance, then FAISS lookup map.
        distance = doc.metadata.get("retrieval_distance")
        if distance is None and score_by_key is not None:
            distance = score_by_key.get(key)
            if distance is None:
                # Fallback: match on content prefix only.
                for sk, dist in score_by_key.items():
                    if sk[2] == key[2]:
                        distance = dist
                        break
        if distance is not None:
            try:
                dist_f = float(distance)
                entry["distance"] = dist_f
                sim = confidence_service.distance_to_similarity(dist_f)
                if sim is not None:
                    entry["retrieval_score"] = round(sim, 4)
            except (TypeError, ValueError):
                pass
        sources.append(entry)
    if not sources:
        sources.append(
            {
                "filename": document.original_filename,
                "document_id": document.id,
                "type": "legal_document",
            }
        )
    return sources


def _faiss_score_map(document: Document, query: str, k: int) -> dict[tuple, float]:
    """Map chunk keys → FAISS L2 distance for confidence (never fabricated)."""
    try:
        store = load_vector_store(
            get_embeddings_model(), persist_path=document.index_path
        )
        scored = store.similarity_search_with_score(query, k=max(1, k))
    except Exception as exc:
        logger.warning("FAISS score lookup failed for confidence: %s", exc)
        return {}
    mapping: dict[tuple, float] = {}
    for doc, distance in scored:
        page = doc.metadata.get("page_number") or doc.metadata.get("page")
        content_type = doc.metadata.get("content_type", "text")
        key = (page, content_type, doc.page_content[:80])
        try:
            mapping[key] = float(distance)
        except (TypeError, ValueError):
            continue
    return mapping


def _prepare_ask(db: Session, user: User, document_id: str, question: str):
    document = document_service.require_ready_document(db, user, document_id)
    rag = get_or_create_rag(db, user, document)

    if rag.chat_history:
        standalone = rag.contextualize_chain.invoke(
            {"input": question, "chat_history": rag.chat_history}
        )
    else:
        standalone = question

    retrieve_started = time.perf_counter()
    try:
        docs = rag.retriever.invoke(standalone)
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="retrieval failed",
            user_id=user.id,
            document_id=document.id,
            error_type=type(exc).__name__,
        )
        raise RetrievalError(details={"type": type(exc).__name__}) from exc
    retrieve_ms = round((time.perf_counter() - retrieve_started) * 1000, 2)
    log_event(
        logger,
        "retrieval",
        message="chunks retrieved",
        user_id=user.id,
        document_id=document.id,
        chunk_count=len(docs),
        latency_ms=retrieve_ms,
        k=settings.RETRIEVAL_K,
    )

    from src.llm.formatting import format_docs

    score_map = _faiss_score_map(
        document, standalone, max(len(docs), settings.RETRIEVAL_K)
    )
    context = format_docs(docs)
    sources = _sources_from_docs(document, docs, score_by_key=score_map)
    question_type = classify_question(question, llm=rag.llm)
    return rag, document, standalone, context, docs, sources, question_type


def _confidence_payload(confidence: confidence_service.ConfidenceResult) -> dict:
    return {
        "confidence_score": confidence.confidence_score,
        "confidence_level": confidence.confidence_level,
        "recommendation": confidence.recommendation,
        "confidence_factors": confidence.factors,
    }


def _finalize_text_answer(
    answer: str,
    sources: list[dict],
    *,
    chunk_count: int | None = None,
) -> tuple[str, confidence_service.ConfidenceResult]:
    from src.safety.guardrails import sanitize_legal_output

    # Strip Legal Advice / forbidden claims before confidence scoring.
    safe_answer, violations = sanitize_legal_output(answer)
    if violations:
        log_event(
            logger,
            "safety_violation",
            level=logging.WARNING,
            message="unsafe legal output sanitized",
            violation_codes=violations,
        )
        answer = safe_answer

    conf = confidence_service.estimate_for_text_answer(
        answer=answer,
        sources=sources,
        chunk_count=chunk_count,
        target_k=max(3, settings.RETRIEVAL_K),
    )
    finalized = confidence_service.apply_confidence_policy(answer, conf)
    # Re-check after policy append (medium notes are safe; low is generated).
    finalized, post_violations = sanitize_legal_output(finalized)
    if post_violations:
        log_event(
            logger,
            "safety_violation",
            level=logging.WARNING,
            message="post-policy output sanitized",
            violation_codes=post_violations,
        )
    return finalized, conf


def _persist_exchange(
    db: Session,
    document: Document,
    question: str,
    answer: str,
    question_type: str,
    processing_time: float,
    sources: list[dict],
) -> ChatMessage:
    user_msg = ChatMessage(
        document_id=document.id, role="user", content=question
    )
    assistant_msg = ChatMessage(
        document_id=document.id,
        role="assistant",
        content=answer,
        question_type=question_type,
        processing_time=processing_time,
        sources_json=json.dumps(sources),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


def ask_document(
    db: Session,
    user: User,
    document_id: str,
    question: str,
) -> dict:
    start = time.time()
    rag, document, standalone, context, docs, sources, question_type = _prepare_ask(
        db, user, document_id, question
    )

    # No supporting chunks → abstain without calling the LLM.
    if not docs:
        answer = confidence_service.LOW_ABSTENTION
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
        processing_time = round(time.time() - start, 2)
        assistant_msg = _persist_exchange(
            db, document, question, answer, question_type, processing_time, sources
        )
        return {
            "question": question,
            "answer": answer,
            "question_type": question_type,
            "sources": sources,
            "processing_time": processing_time,
            "document_id": document.id,
            "message_id": assistant_msg.id,
            **_confidence_payload(conf),
        }

    llm_started = time.perf_counter()
    log_event(
        logger,
        "llm_request",
        message="llm invoke started",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type=question_type,
    )
    try:
        answer = rag.answer_chain.invoke(
            {
                "input": standalone,
                "context": context,
                "chat_history": rag.chat_history,
            }
        )
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="llm invoke failed",
            user_id=user.id,
            document_id=document.id,
            model=settings.LLM_MODEL,
            error_type=type(exc).__name__,
        )
        raise _map_llm_exception(exc) from exc

    llm_ms = round((time.perf_counter() - llm_started) * 1000, 2)
    log_event(
        logger,
        "llm_request",
        message="llm invoke completed",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type=question_type,
        latency_ms=llm_ms,
    )

    answer, conf = _finalize_text_answer(answer, sources, chunk_count=len(docs))

    rag.chat_history.append(HumanMessage(content=question))
    rag.chat_history.append(AIMessage(content=answer))
    window = settings.CHAT_MEMORY_WINDOW
    if window > 0 and len(rag.chat_history) > window:
        rag.chat_history = rag.chat_history[-window:]

    processing_time = round(time.time() - start, 2)
    assistant_msg = _persist_exchange(
        db, document, question, answer, question_type, processing_time, sources
    )

    return {
        "question": question,
        "answer": answer,
        "question_type": question_type,
        "sources": sources,
        "processing_time": processing_time,
        "document_id": document.id,
        "message_id": assistant_msg.id,
        **_confidence_payload(conf),
    }


def stream_ask_document(
    db: Session,
    user: User,
    document_id: str,
    question: str,
) -> Iterator[str]:
    """Yield SSE-formatted events: meta, token*, done."""
    start = time.time()
    rag, document, standalone, context, docs, sources, question_type = _prepare_ask(
        db, user, document_id, question
    )

    meta = {
        "question_type": question_type,
        "sources": sources,
    }
    yield f"event: meta\ndata: {json.dumps(meta)}\n\n"

    if not docs:
        answer = confidence_service.LOW_ABSTENTION
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
        processing_time = round(time.time() - start, 2)
        assistant_msg = _persist_exchange(
            db, document, question, answer, question_type, processing_time, sources
        )
        done = {
            "answer": answer,
            "question_type": question_type,
            "sources": sources,
            "processing_time": processing_time,
            "document_id": document.id,
            "message_id": assistant_msg.id,
            **_confidence_payload(conf),
        }
        yield f"event: done\ndata: {json.dumps(done)}\n\n"
        return

    llm_started = time.perf_counter()
    log_event(
        logger,
        "llm_request",
        message="llm stream started",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type=question_type,
        streaming=True,
    )
    pieces: list[str] = []
    try:
        for chunk in rag.answer_chain.stream(
            {
                "input": standalone,
                "context": context,
                "chat_history": rag.chat_history,
            }
        ):
            text = chunk if isinstance(chunk, str) else str(chunk)
            pieces.append(text)
            yield f"event: token\ndata: {json.dumps({'token': text})}\n\n"
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="llm stream failed",
            user_id=user.id,
            document_id=document.id,
            model=settings.LLM_MODEL,
            error_type=type(exc).__name__,
        )
        raise _map_llm_exception(exc) from exc

    llm_ms = round((time.perf_counter() - llm_started) * 1000, 2)
    log_event(
        logger,
        "llm_request",
        message="llm stream completed",
        user_id=user.id,
        document_id=document.id,
        model=settings.LLM_MODEL,
        question_type=question_type,
        latency_ms=llm_ms,
        streaming=True,
    )

    raw_answer = "".join(pieces)
    answer, conf = _finalize_text_answer(
        raw_answer, sources, chunk_count=len(docs)
    )
    # If policy rewrote the answer (Low/Medium note), send a replace token block
    # so clients that only streamed tokens still see the final text from `done`.
    rag.chat_history.append(HumanMessage(content=question))
    rag.chat_history.append(AIMessage(content=answer))
    window = settings.CHAT_MEMORY_WINDOW
    if window > 0 and len(rag.chat_history) > window:
        rag.chat_history = rag.chat_history[-window:]

    processing_time = round(time.time() - start, 2)
    assistant_msg = _persist_exchange(
        db, document, question, answer, question_type, processing_time, sources
    )

    done = {
        "answer": answer,
        "question_type": question_type,
        "sources": sources,
        "processing_time": processing_time,
        "document_id": document.id,
        "message_id": assistant_msg.id,
        **_confidence_payload(conf),
    }
    yield f"event: done\ndata: {json.dumps(done)}\n\n"


def compare_documents(
    db: Session,
    user: User,
    document_id_a: str,
    document_id_b: str,
    question: str,
) -> dict:
    start = time.time()
    doc_a = document_service.require_ready_document(db, user, document_id_a)
    doc_b = document_service.require_ready_document(db, user, document_id_b)

    embeddings = get_embeddings_model()
    llm = get_llm()
    store_a = load_vector_store(embeddings, persist_path=doc_a.index_path)
    store_b = load_vector_store(embeddings, persist_path=doc_b.index_path)
    retrieve_started = time.perf_counter()
    try:
        scored_a = store_a.similarity_search_with_score(
            question, k=settings.RETRIEVAL_K
        )
        scored_b = store_b.similarity_search_with_score(
            question, k=settings.RETRIEVAL_K
        )
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="compare retrieval failed",
            user_id=user.id,
            error_type=type(exc).__name__,
        )
        raise RetrievalError(details={"type": type(exc).__name__}) from exc

    docs_a = []
    score_map_a: dict[tuple, float] = {}
    for doc, distance in scored_a:
        page = doc.metadata.get("page_number") or doc.metadata.get("page")
        content_type = doc.metadata.get("content_type", "text")
        score_map_a[(page, content_type, doc.page_content[:80])] = float(distance)
        docs_a.append(doc)
    docs_b = []
    score_map_b: dict[tuple, float] = {}
    for doc, distance in scored_b:
        page = doc.metadata.get("page_number") or doc.metadata.get("page")
        content_type = doc.metadata.get("content_type", "text")
        score_map_b[(page, content_type, doc.page_content[:80])] = float(distance)
        docs_b.append(doc)

    log_event(
        logger,
        "retrieval",
        message="compare chunks retrieved",
        user_id=user.id,
        document_id=document_id_a,
        document_id_b=document_id_b,
        chunk_count=len(docs_a) + len(docs_b),
        latency_ms=round((time.perf_counter() - retrieve_started) * 1000, 2),
        k=settings.RETRIEVAL_K,
    )

    sources_a = _sources_from_docs(doc_a, docs_a, score_by_key=score_map_a)
    sources_b = _sources_from_docs(doc_b, docs_b, score_by_key=score_map_b)
    offset = len([s for s in sources_a if s.get("index") is not None])
    for src in sources_b:
        if src.get("index") is not None:
            src["index"] = int(src["index"]) + offset
    sources = sources_a + sources_b

    def fmt(label: str, docs, index_start: int) -> str:
        parts = []
        for i, d in enumerate(docs):
            page = d.metadata.get("page_number") or d.metadata.get("page", "?")
            parts.append(
                f"[Source {index_start + i} | page {page} | {label}]\n{d.page_content}"
            )
        return f"=== {label} ===\n" + "\n\n".join(parts)

    if not docs_a and not docs_b:
        answer = confidence_service.LOW_ABSTENTION
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
        processing_time = round(time.time() - start, 2)
        return {
            "question": question,
            "answer": answer,
            "question_type": "general",
            "sources": sources,
            "processing_time": processing_time,
            "document_id": document_id_a,
            "document_id_b": document_id_b,
            "message_id": None,
            **_confidence_payload(conf),
        }

    from src.safety.prompts import with_safety_preamble

    prompt = with_safety_preamble(
        "You are a document analyst comparing two contract excerpts "
        "(Legal Information only).\n"
        "Highlight similarities, differences, and risks as written. "
        "Cite evidence using [Source N] markers from the context.\n"
        "Never predict court outcomes or tell the user what legal action to take.\n\n"
        f"Question: {question}\n\n"
        f"{fmt(doc_a.original_filename, docs_a, 1)}\n\n"
        f"{fmt(doc_b.original_filename, docs_b, 1 + len(docs_a))}"
    )
    llm_started = time.perf_counter()
    log_event(
        logger,
        "llm_request",
        message="compare llm invoke started",
        user_id=user.id,
        document_id=document_id_a,
        model=settings.LLM_MODEL,
    )
    try:
        answer = llm.invoke(prompt).content
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            message="compare llm invoke failed",
            user_id=user.id,
            error_type=type(exc).__name__,
        )
        raise _map_llm_exception(exc) from exc
    log_event(
        logger,
        "llm_request",
        message="compare llm invoke completed",
        user_id=user.id,
        document_id=document_id_a,
        model=settings.LLM_MODEL,
        latency_ms=round((time.perf_counter() - llm_started) * 1000, 2),
    )
    answer, conf = _finalize_text_answer(
        answer if isinstance(answer, str) else str(answer),
        sources,
        chunk_count=len(docs_a) + len(docs_b),
    )
    processing_time = round(time.time() - start, 2)
    return {
        "question": question,
        "answer": answer,
        "question_type": "general",
        "sources": sources,
        "processing_time": processing_time,
        "document_id": document_id_a,
        "document_id_b": document_id_b,
        "message_id": None,
        **_confidence_payload(conf),
    }


def reset_conversation(db: Session, user: User, document_id: str) -> None:
    document_service.clear_chat_history(db, user, document_id)
    if document_id in _rag_cache:
        _rag_cache[document_id].reset_memory()
    logger.info("Conversation reset user=%s doc=%s", user.id, document_id)
