"""
Checkpoint/resume for long-running benchmark executions.

Sprint 3 benchmark-robustness fix: RAGAS scoring makes hundreds of direct OpenAI
calls per 141-sample run and can be interrupted by a killed process, a session
timeout, or (as observed this session, via the new retry logging) sustained
OpenAI rate-limiting — all external to this codebase. Without this module, any
interruption meant redoing the *entire* run from scratch, discarding real,
already-paid-for OpenAI spend. This module persists each sample's pipeline
result (retrieval + generation) and RAGAS scores to disk immediately as they
complete, so a resumed run skips everything already done and only computes
what's missing.

Checkpoints are keyed by (dataset_version, exact model/retrieval config) — see
`environment.model_config_snapshot()` — so a checkpoint from one experiment
(e.g. CHUNK_SIZE=256) can never be silently reused by a different one (e.g.
CHUNK_SIZE=384). Writes are atomic (write-to-temp + rename) so a crash mid-write
cannot corrupt the checkpoint file itself.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.evaluation.benchmark import environment
from src.evaluation.benchmark.dataset import BenchmarkSample
from src.evaluation.benchmark.runner import SampleResult

CHECKPOINT_DIR = environment.BENCHMARK_DIR / ".state" / "checkpoints"

_EMPTY: dict[str, Any] = {"pipeline_results": {}, "scores": {}}


def checkpoint_path(dataset_version: str, model_config: dict) -> Path:
    """One checkpoint file per exact (dataset, retrieval/model config) combination."""
    slug = "_".join(f"{k}-{v}" for k, v in sorted(model_config.items()))
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINT_DIR / f"{dataset_version}__{slug}.json"


def load_checkpoint(path: Path) -> dict:
    if not path.exists():
        return {"pipeline_results": {}, "scores": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)  # atomic on the same filesystem — no half-written checkpoint


def _sample_result_to_dict(result: SampleResult) -> dict:
    data = asdict(result)
    data.pop("sample")  # static per dataset version — reloaded from the dataset file
    return data


def save_pipeline_result(path: Path, sample_id: str, result: SampleResult) -> None:
    """Persist one sample's pipeline (retrieval+generation) result immediately —
    called right after that sample completes, not batched."""
    checkpoint = load_checkpoint(path)
    checkpoint["pipeline_results"][sample_id] = _sample_result_to_dict(result)
    _atomic_write(path, checkpoint)


def save_score(path: Path, sample_id: str, scores: dict) -> None:
    """Persist one sample's RAGAS scores immediately after that sample is scored."""
    checkpoint = load_checkpoint(path)
    checkpoint["scores"][sample_id] = scores
    _atomic_write(path, checkpoint)


def rebuild_sample_result(sample: BenchmarkSample, pipeline_data: dict) -> SampleResult:
    """Reconstruct a full SampleResult from a checkpointed pipeline result plus the
    freshly-loaded BenchmarkSample (samples are static per dataset version, so
    re-loading from the dataset file is always correct and avoids persisting
    redundant data)."""
    return SampleResult(sample=sample, **pipeline_data)


def progress_summary(checkpoint: dict, total_samples: int) -> str:
    pipeline_done = len(checkpoint["pipeline_results"])
    scored_done = len(checkpoint["scores"])
    return (
        f"checkpoint found: {pipeline_done}/{total_samples} samples processed, "
        f"{scored_done}/{total_samples} scored"
    )
