"""
Sprint 2A Task 1 — performance instrumentation for the benchmark harness.

This module measures the production RAG pipeline without changing it. No file under
``backend/src/services``, ``backend/src/retrieval``, ``backend/src/llm``, or
``backend/src/ingestion`` is modified by Sprint 2A Task 1 — every number below is
obtained by either (a) reading structured log events `rag_service` already emits, or
(b) scoped, reversible instrumentation installed and removed entirely from here.

Four latency numbers, deliberately not mutually exclusive (see class docstring):

- ``retrieval_latency_ms`` — read directly from the ``"retrieval"`` structured log
  event `rag_service._prepare_ask` already emits around ``rag.retriever.invoke(...)``.
  This is the dense+BM25 combine step only.
- ``generation_latency_ms`` — read directly from the ``"llm_request"`` (completed)
  structured log event `rag_service.ask_document` already emits around
  ``rag.answer_chain.invoke(...)``. This is the answer-generation call only.
- ``embedding_latency_ms`` / ``embedding_call_count`` — measured by temporarily wrapping
  the *shared* embeddings client's ``embed_query`` method (instance-scoped — see below).
  Every embedding call in the app — the dense retriever's own query embed, and
  `_faiss_score_map`'s separate confidence-scoring embed — goes through this one client
  instance (`rag_service.get_embeddings_model()` is a process-wide `@lru_cache`
  singleton), so wrapping it once here captures every embedding call made during the
  profiled request. This number is *not* a disjoint slice of wall-clock time from
  ``retrieval_latency_ms`` — it is a cross-cutting measurement of how much of the total
  request time was spent specifically inside OpenAI embedding calls (retrieval also
  spends time on local BM25/FAISS compute that this number does not include).
- ``prompt_tokens`` / ``completion_tokens`` / ``total_tokens`` / ``chat_cost_usd`` —
  read from LangChain's ``get_openai_callback()`` context manager, which transparently
  tracks token usage/cost for every nested ``ChatOpenAI`` call made inside the ``with``
  block (the answer generation call, and the question-classification call if
  ``USE_LLM_CLASSIFIER`` is enabled) without needing access to where those calls are
  made. Verified directly against this repo's configured model
  (`gpt-4o-mini`): it reports real, API-derived token counts and a real cost estimate.

Embedding token counts are *estimated* (via ``tiktoken``), not read from the OpenAI
response, because LangChain's ``Embeddings.embed_query`` wrapper does not expose the
API response's own ``usage`` field to the caller. The estimate uses the same tokenizer
OpenAI's embedding models use.

Instance-scoped, cache-aware patching (composes with Sprint 2A Task 2)
------------------------------------------------------------------------
``OpenAIEmbeddings`` is a Pydantic model — it rejects plain attribute assignment
(``obj.embed_query = ...`` raises ``ValueError: object has no field "embed_query"``),
so ``object.__setattr__`` is used to shadow the method on this one instance only
(verified safe: Pydantic v2 instances still resolve instance-``__dict__`` overrides
ahead of class methods on normal attribute access).

Critically, this wraps *whatever `embed_query` currently resolves to on the instance*
(via ``getattr``), not the raw class method — after Sprint 2A Task 2 installs its own
permanent per-instance memoizing wrapper (`services/query_embedding_cache.py`), that
wrapper exposes a ``cache_info()`` (the same interface `functools.lru_cache` exposes).
When present, each individual call snapshots hit/miss counts immediately before and
after itself to determine whether *that specific call* was served from cache — a hit
costs no tokens/dollars (no network call was made), so only misses are counted toward
``estimated_embedding_tokens``/``embedding_cost_usd``. Before Task 2 ships (no cache
installed), every call is necessarily a miss, so the numbers reduce to "count every
call" — backward-compatible by construction, not by special-casing.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass

import tiktoken
from langchain_community.callbacks import get_openai_callback

from src.logging_config import logger as app_logger

# Static per-1K-token prices (USD). Config-driven, not hardcoded into any scoring
# logic — this is the only place these numbers live, per OPTIMIZATION_PLAN.md's
# guidance to keep pricing out of business logic and easy to update.
PRICE_PER_1K_TOKENS_USD = {
    "text-embedding-3-small": 0.00002,
}


@dataclass
class RequestProfile:
    retrieval_latency_ms: float | None = None
    generation_latency_ms: float | None = None
    embedding_latency_ms: float = 0.0
    embedding_call_count: int = 0
    embedding_cache_hits: int = 0
    embedding_cache_misses: int = 0
    estimated_embedding_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    chat_cost_usd: float = 0.0
    embedding_cost_usd: float = 0.0

    @property
    def total_cost_usd(self) -> float:
        return round(self.chat_cost_usd + self.embedding_cost_usd, 8)


class _LatencyLogCapture(logging.Handler):
    """Reads the exact latency numbers `rag_service` already logs, without changing
    what it logs or how — a passive listener attached only for the profiled call."""

    def __init__(self) -> None:
        super().__init__()
        self.retrieval_latency_ms: float | None = None
        self.generation_latency_ms: float | None = None

    def emit(self, record: logging.LogRecord) -> None:
        event = getattr(record, "event", None)
        latency_ms = getattr(record, "latency_ms", None)
        if latency_ms is None:
            return
        if event == "retrieval":
            self.retrieval_latency_ms = latency_ms
        elif event == "llm_request":
            # Only the "...completed" log_event call carries latency_ms; the
            # "...started" call does not, so this can't match the wrong one.
            self.generation_latency_ms = latency_ms


def _encoding_for(model: str) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def _cache_hit_count(embed_query_callable) -> int | None:
    """Cumulative hit count if `embed_query` exposes a `functools.lru_cache`-style
    `cache_info()` (i.e. Sprint 2A Task 2's cache is installed), else None."""
    cache_info = getattr(embed_query_callable, "cache_info", None)
    if cache_info is None:
        return None
    return cache_info().hits


@contextmanager
def profile_request(embeddings_client, embedding_model: str):
    """
    Measure exactly one production call. Construct a fresh context manager per call
    you want profiled — this is not meant to span an entire benchmark run, only the
    single ``rag_service.ask_document(...)`` invocation being measured, so that the
    numbers reflect one real request, not the harness's own extra diagnostic calls.
    """
    profile = RequestProfile()
    log_capture = _LatencyLogCapture()
    app_logger.addHandler(log_capture)

    encoding = _encoding_for(embedding_model)

    # Capture whatever is *currently* installed (the raw method, or Task 2's cache
    # wrapper) — not the class's original method — so this composes correctly
    # regardless of whether Task 2 has shipped yet.
    current_embed_query = getattr(embeddings_client, "embed_query")

    def _wrapped_embed_query(text, *args, **kwargs):
        started = time.perf_counter()
        hits_before = _cache_hit_count(current_embed_query)
        result = current_embed_query(text, *args, **kwargs)
        elapsed_ms = (time.perf_counter() - started) * 1000
        hits_after = _cache_hit_count(current_embed_query)

        profile.embedding_call_count += 1
        profile.embedding_latency_ms += elapsed_ms

        was_hit = (
            hits_before is not None
            and hits_after is not None
            and hits_after > hits_before
        )
        if was_hit:
            profile.embedding_cache_hits += 1
        else:
            # No cache installed (pre-Task-2), or a real cache miss either way:
            # this call reached the network and incurred real tokens/cost.
            profile.embedding_cache_misses += 1
            profile.estimated_embedding_tokens += len(encoding.encode(text))

        return result

    object.__setattr__(embeddings_client, "embed_query", _wrapped_embed_query)
    try:
        with get_openai_callback() as cb:
            yield profile
        profile.prompt_tokens = cb.prompt_tokens
        profile.completion_tokens = cb.completion_tokens
        profile.total_tokens = cb.total_tokens
        profile.chat_cost_usd = cb.total_cost
    finally:
        object.__setattr__(embeddings_client, "embed_query", current_embed_query)
        app_logger.removeHandler(log_capture)
        profile.retrieval_latency_ms = log_capture.retrieval_latency_ms
        profile.generation_latency_ms = log_capture.generation_latency_ms
        price_per_token = PRICE_PER_1K_TOKENS_USD.get(embedding_model, 0.0) / 1000
        profile.embedding_cost_usd = round(
            profile.estimated_embedding_tokens * price_per_token, 8
        )
