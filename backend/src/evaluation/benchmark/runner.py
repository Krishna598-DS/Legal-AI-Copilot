"""
Runs a benchmark dataset through the *real* production RAG pipeline.

This is the fix for the divergence noted in ``RAG_EVALUATION_ARCHITECTURE.md`` Section 1:
the previous evaluation harness (`src/evaluation/evaluator.py`) built its own
non-conversational chain (`llm/rag_chain.py`) and therefore skipped safety scrubbing and
confidence scoring — it did not evaluate what users actually receive. This module instead
calls the same ``rag_service`` functions the HTTP layer calls.

Two production calls are made per benchmark question:

1. ``rag_service._prepare_ask`` — to capture the raw retrieved chunk text as RAGAS
   "contexts". This is the exact retrieval step both the streaming and non-streaming
   production answer paths already share; it is not a separate/duplicated retrieval
   implementation. This call is *not* instrumented (Sprint 2A) — it is harness-only
   diagnostic overhead, not representative of a real user request.
2. ``rag_service.ask_document`` — the public production entrypoint, including safety
   guardrail scrubbing and confidence scoring, for the final answer users would see.
   This is the call Sprint 2A's ``instrumentation.profile_request`` wraps, since it is
   exactly what one real user request executes.

Retrieval therefore runs twice per benchmark question (``ask_document`` calls
``_prepare_ask`` again internally). This is a deliberate, accepted Sprint 1 tradeoff:
it costs a second (cheap, local) FAISS/BM25 lookup and, if ``USE_LLM_CLASSIFIER`` is on,
a second small classification call — but it means zero changes were required to
production code to get faithful evaluation. Sprint 2A Task 2 addresses the *production*
side of this duplication (the confidence-scoring re-embed inside ``_prepare_ask``
itself); the harness's own extra diagnostic call is a separate, accepted cost of
measurement, not a production inefficiency, and is unaffected by Task 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.evaluation.benchmark import environment
from src.evaluation.benchmark.dataset import BenchmarkDataset, BenchmarkSample
from src.evaluation.benchmark.instrumentation import RequestProfile, profile_request
from src.services import rag_service

_EMPTY_CHECKPOINT: dict = {"pipeline_results": {}, "scores": {}}


@dataclass
class SampleResult:
    sample: BenchmarkSample
    answer: str
    contexts: list[str]
    retrieved_chunk_count: int
    confidence_score: float | None
    confidence_level: str | None
    end_to_end_latency_s: float
    # Sprint 2A Task 1 — see instrumentation.py for exactly what each of these means
    # and how it's measured. All default to "empty" values so error-path SampleResults
    # (which never reach the profiled call) serialize cleanly.
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
    total_cost_usd: float = 0.0
    # The exact confidence-policy note (if any) `confidence_service.apply_confidence_policy`
    # appended to `answer` (see `services/confidence.py::apply_confidence_policy`). Captured
    # so `ragas_eval.py` can score the substantive answer text separately from this
    # boilerplate — see the module docstring there for why that distinction matters.
    confidence_note: str | None = None
    # Sprint 2A Task 3 — the question_type production actually routed to
    # (general/financial/risk), captured so classifier changes can be checked
    # directly against what routing changed, not just inferred from score deltas.
    classified_question_type: str | None = None
    error: str | None = None


def _apply_profile(result: SampleResult, profile: RequestProfile) -> SampleResult:
    result.retrieval_latency_ms = profile.retrieval_latency_ms
    result.generation_latency_ms = profile.generation_latency_ms
    result.embedding_latency_ms = round(profile.embedding_latency_ms, 2)
    result.embedding_call_count = profile.embedding_call_count
    result.embedding_cache_hits = profile.embedding_cache_hits
    result.embedding_cache_misses = profile.embedding_cache_misses
    result.estimated_embedding_tokens = profile.estimated_embedding_tokens
    result.prompt_tokens = profile.prompt_tokens
    result.completion_tokens = profile.completion_tokens
    result.total_tokens = profile.total_tokens
    result.chat_cost_usd = profile.chat_cost_usd
    result.embedding_cost_usd = profile.embedding_cost_usd
    result.total_cost_usd = profile.total_cost_usd
    return result


def _run_sample(db, user, document, sample: BenchmarkSample) -> SampleResult:
    # Each benchmark question is an independent, single-shot question — not a multi-turn
    # conversation — so conversational memory from a prior sample against the same fixture
    # document must not leak into this one's retrieval/answer.
    rag_service.reset_conversation(db, user, document.id)

    try:
        _rag, _document, _standalone, _context, docs, _sources, _question_type = (
            rag_service._prepare_ask(db, user, document.id, sample.question)
        )
    except Exception as exc:  # noqa: BLE001 - surfaced in the report, not swallowed
        return SampleResult(
            sample=sample,
            answer="",
            contexts=[],
            retrieved_chunk_count=0,
            confidence_score=None,
            confidence_level=None,
            end_to_end_latency_s=0.0,
            error=f"retrieval failed: {exc}",
        )
    contexts = [d.page_content for d in docs]

    embeddings_client = rag_service.get_embeddings_model()
    embedding_model = environment.settings.EMBEDDING_MODEL

    # The harness's own diagnostic `_prepare_ask` probe call just above already embedded
    # `sample.question` once, which (after Sprint 2A Task 2) would leave the query-embedding
    # cache pre-warmed before the *profiled* call below even starts — making every profiled
    # call look like 100% cache hits, which is an artifact of this harness's two-call-per-
    # sample design (see runner.py module docstring), not representative of a real single
    # production request. Clearing the cache here means the profiled call below sees the
    # same "have I embedded this exact text before in this process" state a genuinely new
    # user question would: one real miss (the retrieval step's own embed) followed by one
    # real hit (the confidence-scoring re-embed Task 2 targets) — the true production
    # pattern this instrumentation is meant to demonstrate.
    cache_clear = getattr(embeddings_client.embed_query, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()

    try:
        with profile_request(embeddings_client, embedding_model) as profile:
            result = rag_service.ask_document(db, user, document.id, sample.question)
    except Exception as exc:  # noqa: BLE001
        return SampleResult(
            sample=sample,
            answer="",
            contexts=contexts,
            retrieved_chunk_count=len(docs),
            confidence_score=None,
            confidence_level=None,
            end_to_end_latency_s=0.0,
            error=f"generation failed: {exc}",
        )

    sample_result = SampleResult(
        sample=sample,
        answer=result["answer"],
        contexts=contexts,
        retrieved_chunk_count=len(docs),
        confidence_score=result.get("confidence_score"),
        confidence_level=result.get("confidence_level"),
        end_to_end_latency_s=result.get("processing_time", 0.0),
        confidence_note=result.get("recommendation") or None,
        classified_question_type=result.get("question_type"),
    )
    return _apply_profile(sample_result, profile)


async def run_benchmark(
    dataset: BenchmarkDataset, checkpoint_path: Path | None = None
) -> list[SampleResult]:
    """`checkpoint_path`, if given, is a checkpoint file (see `checkpoint.py`) keyed
    to this exact dataset + retrieval/model config. Samples already present in it
    are reused as-is (no re-run of retrieval/generation); every newly-computed
    sample is persisted to it immediately, not batched, so an interruption loses
    at most the one sample in flight."""
    # Imported lazily: `checkpoint.py` imports `SampleResult` from this module, so a
    # top-level import here would be circular.
    from src.evaluation.benchmark import checkpoint as checkpoint_mod

    environment.ensure_environment()
    db = environment.SessionLocal()
    try:
        user = environment.get_or_create_benchmark_user(db)
        environment.reset_benchmark_documents(db, user)
        doc_map = await environment.ingest_fixture_documents(db, user, dataset.documents_dir)

        checkpoint = (
            checkpoint_mod.load_checkpoint(checkpoint_path)
            if checkpoint_path
            else _EMPTY_CHECKPOINT
        )

        results: list[SampleResult] = []
        for sample in dataset.samples:
            cached = checkpoint["pipeline_results"].get(sample.id)
            if cached is not None:
                results.append(checkpoint_mod.rebuild_sample_result(sample, cached))
                continue

            document = doc_map.get(sample.source_document_id)
            if document is None:
                result = SampleResult(
                    sample=sample,
                    answer="",
                    contexts=[],
                    retrieved_chunk_count=0,
                    confidence_score=None,
                    confidence_level=None,
                    end_to_end_latency_s=0.0,
                    error=(
                        f"fixture document '{sample.source_document_id}' "
                        "not found among ingested documents"
                    ),
                )
            else:
                result = _run_sample(db, user, document, sample)

            results.append(result)
            if checkpoint_path:
                checkpoint_mod.save_pipeline_result(checkpoint_path, sample.id, result)
        return results
    finally:
        db.close()
