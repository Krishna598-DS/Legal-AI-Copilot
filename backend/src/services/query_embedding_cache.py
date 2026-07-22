"""
Sprint 2A Task 2 — eliminate the duplicate query-embedding call.

Finding (documented in ``OPTIMIZATION_PLAN.md`` Section 1/2): ``rag_service._prepare_ask``
embeds the same standalone query string twice per question — once inside
``rag.retriever.invoke(standalone)`` (the dense leg of the hybrid retriever) and again
inside ``_faiss_score_map(document, standalone, ...)`` (a second, independent
``similarity_search_with_score`` call made solely to recover numeric distances for
``confidence_service``, since the ensemble retriever's returned ``Document`` objects
don't carry the dense retriever's raw score).

This module memoizes ``embed_query`` on the shared embeddings singleton
(``rag_service.get_embeddings_model()``) so the second, identical call is served from
cache instead of making a second OpenAI API round trip. This is safe and does not change
retrieval behavior or results: embeddings are a pure, deterministic function of
(model, text) — an identical input always produces an identical vector, regardless of
which document or search it's later used against, so reusing a cached vector for
identical text can never make retrieval return something different than a fresh call
would have. Only the *duplicate network round trip* is removed, not any computation
that affects what gets retrieved or answered.

Scoped to the *instance*, not the class: ``OpenAIEmbeddings`` is a Pydantic model,
which rejects plain attribute assignment (``obj.embed_query = ...`` raises
``ValueError: object has no field "embed_query"``), so installation uses
``object.__setattr__`` to shadow the method on this one object only — the separate
``OpenAIEmbeddings`` instance ``document_service.run_ingestion_job`` constructs at
upload time (via ``ingestion.embeddings.create_embeddings()`` directly, bypassing this
singleton) is completely unaffected.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

_CACHE_MARKER = "_query_embedding_cache_installed"


def install_query_embedding_cache(embeddings: Any, maxsize: int = 256) -> None:
    """Idempotent: safe to call every time the singleton is constructed."""
    if getattr(embeddings, _CACHE_MARKER, False):
        return

    original_embed_query = embeddings.embed_query  # bound method, this instance only

    @lru_cache(maxsize=maxsize)
    def _cached(text: str) -> tuple[float, ...]:
        return tuple(original_embed_query(text))

    def _embed_query_cached(text: str, *args: Any, **kwargs: Any) -> list[float]:
        return list(_cached(text))

    # Exposed so the evaluation harness can measure exact cache hit/miss counts per
    # request (see `evaluation/benchmark/instrumentation.py`) rather than guessing.
    _embed_query_cached.cache_info = _cached.cache_info
    _embed_query_cached.cache_clear = _cached.cache_clear

    object.__setattr__(embeddings, "embed_query", _embed_query_cached)
    object.__setattr__(embeddings, _CACHE_MARKER, True)
