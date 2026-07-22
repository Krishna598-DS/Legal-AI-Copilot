"""
Persist evaluation run results as JSON for future-run comparison.

Sprint 1 uses JSON files (one per run) rather than a database — acceptable per the
Sprint 1 scope in ``RAG_EVALUATION_ARCHITECTURE.md``, whose Section 6 database design
(``evaluation_runs`` / ``evaluation_results`` / ``aggregate_scores`` tables) this JSON
shape mirrors closely, so migrating to a real database later is a storage-layer change,
not a rethink of what data is captured.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.benchmark import environment
from src.evaluation.benchmark.environment import BENCHMARK_DIR
from src.evaluation.benchmark.ragas_eval import ScoredSample, aggregate_scores

RESULTS_DIR = BENCHMARK_DIR / "results"
RUNS_DIR = RESULTS_DIR / "runs"


def _git_sha() -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=BENCHMARK_DIR.parents[1],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


def build_run_record(dataset_version: str, scored: list[ScoredSample]) -> dict:
    """Snapshot the model/retrieval configuration alongside the scores, so a later
    score delta can always be attributed to a specific system change — not guessed."""
    return {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_version": dataset_version,
        "git_commit": _git_sha(),
        "model_config": environment.model_config_snapshot(),
        "aggregate_scores": aggregate_scores(scored),
        "results": [
            {
                "sample_id": s.result.sample.id,
                "category": s.result.sample.category,
                "difficulty": s.result.sample.difficulty,
                "question_type": s.result.sample.question_type,
                "classified_question_type": s.result.classified_question_type,
                "question": s.result.sample.question,
                "ground_truth_answer": s.result.sample.ground_truth_answer,
                "answer": s.result.answer,
                "confidence_note": s.result.confidence_note,
                "retrieved_chunk_count": s.result.retrieved_chunk_count,
                "confidence_score": s.result.confidence_score,
                "confidence_level": s.result.confidence_level,
                "retrieval_latency_ms": s.result.retrieval_latency_ms,
                "generation_latency_ms": s.result.generation_latency_ms,
                "end_to_end_latency_s": s.result.end_to_end_latency_s,
                "embedding_latency_ms": s.result.embedding_latency_ms,
                "embedding_call_count": s.result.embedding_call_count,
                "embedding_cache_hits": s.result.embedding_cache_hits,
                "embedding_cache_misses": s.result.embedding_cache_misses,
                "estimated_embedding_tokens": s.result.estimated_embedding_tokens,
                "prompt_tokens": s.result.prompt_tokens,
                "completion_tokens": s.result.completion_tokens,
                "total_tokens": s.result.total_tokens,
                "chat_cost_usd": s.result.chat_cost_usd,
                "embedding_cost_usd": s.result.embedding_cost_usd,
                "total_cost_usd": s.result.total_cost_usd,
                "error": s.result.error,
                **s.scores,
            }
            for s in scored
        ],
    }


def persist_run(run_record: dict) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{run_record['run_id']}.json"
    path.write_text(json.dumps(run_record, indent=2), encoding="utf-8")
    return path


def find_previous_run(dataset_version: str, before_run_id: str) -> dict | None:
    """Most recent prior run on the *same* dataset version — comparing across
    dataset versions would conflate a benchmark change with a system change."""
    if not RUNS_DIR.exists():
        return None
    previous: dict | None = None
    for path in sorted(RUNS_DIR.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("run_id", "") >= before_run_id:
            continue
        if record.get("dataset_version") != dataset_version:
            continue
        previous = record  # filenames sort chronologically; keep the latest seen
    return previous
