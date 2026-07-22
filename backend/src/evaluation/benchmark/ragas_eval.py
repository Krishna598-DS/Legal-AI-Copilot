"""Wires benchmark answers into RAGAS: Faithfulness, Answer Relevancy, Context
Precision, Context Recall (the four metrics named in the Sprint 1 scope).

Confirmed empirically while building this Sprint 1 harness: RAGAS's ``answer_relevancy``
metric includes a "noncommittal answer" heuristic that forces the score to exactly ``0.0``
whenever the scored answer text contains hedging/disclaimer-style language. This product's
confidence policy (``services/confidence.py::apply_confidence_policy``) appends exactly that
kind of note — "Confidence: Medium — ... Optional review by a qualified legal professional
is recommended..." — to every Medium-confidence answer. Left unhandled, this made every
Medium-confidence answer in the benchmark score 0.0 on relevancy regardless of whether the
substantive answer actually addressed the question (verified directly: the identical answer
text scored 1.0 with the note removed and 0.0 with it present). This is precisely the kind of
measurement blind spot Sprint 1 Goal #1 (evaluate the real production pipeline, not a
disconnected chain) was meant to surface — the previous, disconnected harness could never
have found this, since it never ran text through the confidence policy at all.

The fix here is scoped to *scoring input*, not production behavior: `_ragas_answer_text`
strips the exact confidence-policy note (captured verbatim by the runner as
`SampleResult.confidence_note`) before handing the answer to RAGAS. The full, unmodified
production text — note included — is still what's persisted and reported everywhere else.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from datasets import Dataset
from langchain_openai import OpenAIEmbeddings
from ragas import RunConfig, evaluate
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

from src.evaluation.benchmark import environment
from src.evaluation.benchmark.runner import SampleResult
from src.services import rag_service

RAGAS_METRICS = [faithfulness, answer_relevancy, context_precision, context_recall]
METRIC_KEYS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")

# Sprint 3 benchmark-robustness fix: RAGAS's library default (max_workers=16) fires
# up to 16 concurrent judge-LLM calls against `rag_service.get_llm()` — a client
# configured with a 60s request_timeout tuned for one interactive user request, not
# bulk scoring. Investigation (see conversation history) traced a run's near-total
# scoring failure (5/141 valid Context Precision samples) to this concurrency level
# saturating the API, not to anything in retrieval/generation (0 pipeline errors
# every time). Lowering to 4 is a config-only change to the evaluation harness; it
# does not touch retrieval, generation, or what is measured.
RAGAS_RUN_CONFIG = RunConfig(max_workers=4, log_tenacity=True)

# Below this fraction of valid (non-null) scores for any metric, the aggregate mean
# is computed over too small/non-representative a sample to trust — see
# `_integrity_check`. 90% chosen as a round, conservative bar: a handful of
# transient failures shouldn't invalidate a run, but the kind of collapse observed
# (e.g. 5/141) must never be reported as if it were a clean number.
MIN_VALID_SAMPLE_RATIO = 0.9


def _enable_ragas_retry_logging() -> None:
    """Surface RAGAS's internal tenacity retry logging so a future failure's console
    output names the actual underlying exception (rate limit, timeout, connection
    reset, ...) instead of only a final bare exception after retries are exhausted.

    Scoped to the root logger only. This app's own production logger (`legal_rag`,
    see `logging_config.py`) sets `propagate=False` and never touches root, so
    nothing here can alter production log output or behavior — this process is
    also the isolated benchmark harness, never the production app server.
    """
    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
        root.addHandler(handler)
    root.setLevel(logging.DEBUG)


@dataclass
class ScoredSample:
    result: SampleResult
    scores: dict[str, float | None] = field(default_factory=dict)


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:  # NaN check without importing pandas/numpy for this alone
        return None
    return round(parsed, 4)


def _ragas_answer_text(result: SampleResult) -> str:
    """The answer text to hand to RAGAS: production text with the confidence-policy
    note stripped (see module docstring). Falls back to the full answer unchanged if
    the exact note isn't present as a trailing suffix (e.g. Low-confidence answers,
    where the whole message *is* the abstention, not an appended note)."""
    if result.confidence_note:
        suffix = f"\n\n{result.confidence_note}"
        if result.answer.endswith(suffix):
            return result.answer[: -len(suffix)]
    return result.answer


def _ragas_inputs(
    results: list[SampleResult],
) -> tuple[dict[str, list], list[int]]:
    """Build the RAGAS input columns, skipping samples that errored before an answer
    was produced. Returns (columns, indices-into-results-that-were-scored)."""
    questions: list[str] = []
    answers: list[str] = []
    contexts: list[list[str]] = []
    ground_truths: list[str] = []
    scored_indices: list[int] = []

    for i, r in enumerate(results):
        if r.error:
            continue
        questions.append(r.sample.question)
        answers.append(_ragas_answer_text(r))
        # RAGAS requires a non-empty context list per row.
        contexts.append(r.contexts or [""])
        ground_truths.append(r.sample.ground_truth_answer)
        scored_indices.append(i)

    columns = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    return columns, scored_indices


def run_ragas(results: list[SampleResult]) -> list[ScoredSample]:
    """Score every non-errored sample with RAGAS; errored samples pass through with
    empty scores so they still appear in the report (as errors, not silently dropped)."""
    scored = [ScoredSample(result=r) for r in results]

    columns, scored_indices = _ragas_inputs(results)
    if not scored_indices:
        return scored

    ragas_dataset = Dataset.from_dict(columns)

    settings = environment.settings
    llm = rag_service.get_llm()
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL, openai_api_key=settings.OPENAI_API_KEY
    )
    _enable_ragas_retry_logging()
    ragas_result = evaluate(
        dataset=ragas_dataset,
        metrics=RAGAS_METRICS,
        llm=llm,
        embeddings=embeddings,
        run_config=RAGAS_RUN_CONFIG,
    )
    scores_df = ragas_result.to_pandas()

    for row_position, original_index in enumerate(scored_indices):
        row = scores_df.iloc[row_position]
        scored[original_index] = ScoredSample(
            result=results[original_index],
            scores={key: _safe_float(row.get(key)) for key in METRIC_KEYS},
        )
    return scored


def _mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 4)


def _slice_summary(items: list[ScoredSample]) -> dict:
    summary = {key: _mean([s.scores.get(key) for s in items]) for key in METRIC_KEYS}
    summary["retrieval_latency_ms"] = _mean([s.result.retrieval_latency_ms for s in items])
    summary["generation_latency_ms"] = _mean([s.result.generation_latency_ms for s in items])
    summary["end_to_end_latency_s"] = _mean([s.result.end_to_end_latency_s for s in items])
    summary["embedding_latency_ms"] = _mean([s.result.embedding_latency_ms for s in items])
    summary["embedding_call_count"] = _mean([s.result.embedding_call_count for s in items])
    summary["embedding_cache_hits"] = _mean([s.result.embedding_cache_hits for s in items])
    summary["embedding_cache_misses"] = _mean(
        [s.result.embedding_cache_misses for s in items]
    )
    summary["estimated_embedding_tokens"] = _mean(
        [s.result.estimated_embedding_tokens for s in items]
    )
    summary["prompt_tokens"] = _mean([s.result.prompt_tokens for s in items])
    summary["completion_tokens"] = _mean([s.result.completion_tokens for s in items])
    summary["total_tokens"] = _mean([s.result.total_tokens for s in items])
    summary["total_cost_usd"] = _mean([s.result.total_cost_usd for s in items])
    summary["confidence_score"] = _mean([s.result.confidence_score for s in items])
    summary["sample_count"] = len(items)
    summary["error_count"] = sum(1 for s in items if s.result.error)
    return summary


def _integrity_check(scored: list[ScoredSample], total_samples: int) -> dict:
    """Sprint 3 benchmark-robustness fix: `_mean` correctly excludes missing/NaN
    scores from its denominator rather than zero-filling them (avoids bias) — but
    that same correct behavior means a run where RAGAS scoring mostly failed (e.g.
    5/141 valid Context Precision samples) can still produce a plausible-looking
    aggregate number with no visible sign anything went wrong. This makes that
    failure mode structurally impossible to miss: every metric's valid/total count
    is checked, and the run is marked invalid if any metric falls below
    `MIN_VALID_SAMPLE_RATIO`."""
    counts: dict[str, dict[str, int]] = {}
    issues: list[str] = []
    for key in METRIC_KEYS:
        valid = sum(1 for s in scored if s.scores.get(key) is not None)
        counts[key] = {"valid": valid, "total": total_samples}
        if total_samples and valid / total_samples < MIN_VALID_SAMPLE_RATIO:
            pct = valid / total_samples
            issues.append(
                f"{key}: only {valid}/{total_samples} samples scored ({pct:.0%}) — "
                f"below the {MIN_VALID_SAMPLE_RATIO:.0%} integrity threshold"
            )
    return {"valid": not issues, "counts": counts, "issues": issues}


def aggregate_scores(scored: list[ScoredSample]) -> dict:
    """Overall + per-category + per-difficulty rollups — the shape the report (and,
    later, a database-backed dashboard) reads directly."""
    by_category: dict[str, list[ScoredSample]] = {}
    by_difficulty: dict[str, list[ScoredSample]] = {}
    for s in scored:
        by_category.setdefault(s.result.sample.category, []).append(s)
        by_difficulty.setdefault(s.result.sample.difficulty, []).append(s)

    return {
        "overall": _slice_summary(scored),
        "by_category": {k: _slice_summary(v) for k, v in by_category.items()},
        "by_difficulty": {k: _slice_summary(v) for k, v in by_difficulty.items()},
        "data_integrity": _integrity_check(scored, len(scored)),
    }
