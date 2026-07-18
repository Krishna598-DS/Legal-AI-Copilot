"""
Confidence estimation for AI legal-document responses.

Scoring logic (deterministic — never LLM-generated)
===================================================

``confidence_score`` is a weighted average in ``[0, 1]`` of four factors:

1. **Retrieval score** (weight 0.35)
   FAISS returns L2 distances (lower = closer). Each distance ``d`` is converted
   with ``similarity = 1 / (1 + d)``. The factor is the mean similarity of the
   retrieved chunks. If no scores are available, this factor is **0.0**
   (conservative — missing evidence never raises confidence).

2. **Supporting chunks** (weight 0.25)
   ``min(1.0, n_chunks / target_k)`` where ``target_k`` defaults to 3.
   Zero chunks → 0.0.

3. **Citation coverage** (weight 0.25)
   ``unique_cited_source_indices / max(1, available_source_indices)``.
   Citations must refer to real retrieved source indices. No citations → 0.0.

4. **Answer grounding** (weight 0.15)
   Heuristic over the answer text (and optional structured evidence ratio):
   - Explicit abstention / “not found” language without citations → 0.2
     (honest but not a grounded positive answer).
   - Presence of ``[Source N]`` markers that match retrieved indices raises
     the score toward 1.0 based on citation density.
   - Structured mode: ``evidence_sections / total_sections`` blended in.
   - Empty answer → 0.0.

``confidence_level`` thresholds (inclusive lower bound):

- **High**   ≥ 0.72
- **Medium** ≥ 0.45
- **Low**    < 0.45

Behavior policy (applied after scoring):

- **High**   — return the answer unchanged.
- **Medium** — return the answer and append an optional expert-review note.
- **Low**    — do **not** return a confident answer; replace with a short
  abstention that recommends consulting a legal professional.

Confidence is never invented by the model. Only these measured signals count.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from src.safety.confidence_messaging import (
    build_low_confidence_message,
    build_medium_confidence_note,
)
from src.safety.policy import CONSULT_PROFESSIONAL

ConfidenceLevel = Literal["High", "Medium", "Low"]

WEIGHT_RETRIEVAL = 0.35
WEIGHT_CHUNKS = 0.25
WEIGHT_CITATIONS = 0.25
WEIGHT_GROUNDING = 0.15

THRESHOLD_HIGH = 0.72
THRESHOLD_MEDIUM = 0.45

DEFAULT_TARGET_CHUNKS = 3

_SOURCE_RE = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)
_NOT_FOUND_RE = re.compile(
    r"(not found in the (provided|retrieved)|no evidence found|"
    r"this information is not found|cannot answer this confidently)",
    re.IGNORECASE,
)

MEDIUM_RECOMMENDATION = build_medium_confidence_note()

LOW_RECOMMENDATION = (
    "Confidence: Low — Do not rely on this output. "
    f"{CONSULT_PROFESSIONAL}"
)

# Default abstention (tests / callers without factor detail).
LOW_ABSTENTION = build_low_confidence_message(None)


@dataclass(frozen=True)
class ConfidenceResult:
    confidence_score: float
    confidence_level: ConfidenceLevel
    recommendation: str
    factors: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "recommendation": self.recommendation,
            "factors": dict(self.factors),
        }


def distance_to_similarity(distance: float | None) -> float | None:
    """Convert FAISS L2 distance to a bounded similarity in (0, 1]."""
    if distance is None:
        return None
    try:
        d = float(distance)
    except (TypeError, ValueError):
        return None
    if d < 0:
        d = 0.0
    return 1.0 / (1.0 + d)


def level_from_score(score: float) -> ConfidenceLevel:
    if score >= THRESHOLD_HIGH:
        return "High"
    if score >= THRESHOLD_MEDIUM:
        return "Medium"
    return "Low"


def recommendation_for(level: ConfidenceLevel) -> str:
    if level == "High":
        return ""
    if level == "Medium":
        return MEDIUM_RECOMMENDATION
    return LOW_RECOMMENDATION


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def retrieval_factor(retrieval_scores: list[float] | None) -> float:
    """Mean converted similarity; missing scores → 0.0 (never fabricated)."""
    if not retrieval_scores:
        return 0.0
    sims: list[float] = []
    for raw in retrieval_scores:
        # Accept either distance or pre-converted similarity in (0, 1].
        # Distances from FAISS are typically > 0 and often > 1; similarities ≤ 1.
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if 0.0 <= value <= 1.0:
            sims.append(value)
        else:
            sim = distance_to_similarity(value)
            if sim is not None:
                sims.append(sim)
    if not sims:
        return 0.0
    return _clamp01(sum(sims) / len(sims))


def chunks_factor(chunk_count: int, target_k: int = DEFAULT_TARGET_CHUNKS) -> float:
    if chunk_count <= 0:
        return 0.0
    target = max(1, int(target_k))
    return _clamp01(chunk_count / target)


def citation_coverage_factor(
    cited_indices: list[int] | set[int] | None,
    available_indices: list[int] | set[int] | None,
) -> float:
    available = {int(i) for i in (available_indices or []) if i is not None}
    if not available:
        return 0.0
    cited = {int(i) for i in (cited_indices or []) if i is not None}
    valid = cited & available
    if not valid:
        return 0.0
    return _clamp01(len(valid) / len(available))


def extract_cited_indices(text: str) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for match in _SOURCE_RE.finditer(text or ""):
        idx = int(match.group(1))
        if idx not in seen:
            seen.add(idx)
            out.append(idx)
    return out


def grounding_factor(
    answer: str,
    *,
    available_indices: list[int] | set[int] | None = None,
    structured_evidence_ratio: float | None = None,
) -> float:
    text = (answer or "").strip()
    if not text and structured_evidence_ratio is None:
        return 0.0

    available = {int(i) for i in (available_indices or []) if i is not None}
    cited = [i for i in extract_cited_indices(text) if not available or i in available]

    score = 0.0
    if cited and available:
        # Density: reward citing a meaningful share of available sources.
        score = 0.45 + 0.55 * _clamp01(len(set(cited)) / len(available))
    elif cited:
        score = 0.55
    elif _NOT_FOUND_RE.search(text):
        score = 0.2
    else:
        # Ungrounded assertive prose — treat as poorly grounded.
        score = 0.1 if text else 0.0

    if structured_evidence_ratio is not None:
        ratio = _clamp01(structured_evidence_ratio)
        score = 0.5 * score + 0.5 * ratio if text else ratio

    return _clamp01(score)


def estimate_confidence(
    *,
    retrieval_scores: list[float] | None = None,
    chunk_count: int = 0,
    cited_indices: list[int] | set[int] | None = None,
    available_indices: list[int] | set[int] | None = None,
    answer: str = "",
    structured_evidence_ratio: float | None = None,
    target_k: int = DEFAULT_TARGET_CHUNKS,
) -> ConfidenceResult:
    """
    Compute confidence from measured retrieval / citation / grounding signals.

    Does not call an LLM. Missing signals lower the score (never inflate it).
    """
    f_retrieval = retrieval_factor(retrieval_scores)
    f_chunks = chunks_factor(chunk_count, target_k=target_k)
    f_citations = citation_coverage_factor(cited_indices, available_indices)
    f_grounding = grounding_factor(
        answer,
        available_indices=available_indices,
        structured_evidence_ratio=structured_evidence_ratio,
    )

    score = _clamp01(
        WEIGHT_RETRIEVAL * f_retrieval
        + WEIGHT_CHUNKS * f_chunks
        + WEIGHT_CITATIONS * f_citations
        + WEIGHT_GROUNDING * f_grounding
    )
    # Stable 2-decimal public score (no fabricated precision beyond inputs).
    score = round(score, 2)
    level = level_from_score(score)
    return ConfidenceResult(
        confidence_score=score,
        confidence_level=level,
        recommendation=recommendation_for(level),
        factors={
            "retrieval_score": round(f_retrieval, 4),
            "supporting_chunks": round(f_chunks, 4),
            "citation_coverage": round(f_citations, 4),
            "answer_grounding": round(f_grounding, 4),
        },
    )


def apply_confidence_policy(answer: str, confidence: ConfidenceResult) -> str:
    """
    Enforce High / Medium / Low answer behavior.

    High   → unchanged (caller should still run safety sanitize)
    Medium → append expert-review recommendation
    Low    → replace with abstention that explains why + consult a professional
    """
    if confidence.confidence_level == "High":
        return answer
    if confidence.confidence_level == "Medium":
        body = (answer or "").rstrip()
        note = confidence.recommendation or MEDIUM_RECOMMENDATION
        if note and note not in body:
            return f"{body}\n\n{note}" if body else note
        return body
    return build_low_confidence_message(confidence.factors)


def scores_from_sources(sources: list[dict] | None) -> list[float]:
    """Collect retrieval distances/similarities attached to source dicts."""
    out: list[float] = []
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        if src.get("retrieval_score") is not None:
            try:
                out.append(float(src["retrieval_score"]))
            except (TypeError, ValueError):
                continue
        elif src.get("distance") is not None:
            try:
                out.append(float(src["distance"]))
            except (TypeError, ValueError):
                continue
    return out


def available_indices_from_sources(sources: list[dict] | None) -> list[int]:
    out: list[int] = []
    for src in sources or []:
        if isinstance(src, dict) and src.get("index") is not None:
            try:
                out.append(int(src["index"]))
            except (TypeError, ValueError):
                continue
    return out


def estimate_for_text_answer(
    *,
    answer: str,
    sources: list[dict] | None,
    chunk_count: int | None = None,
    target_k: int = DEFAULT_TARGET_CHUNKS,
) -> ConfidenceResult:
    cited = extract_cited_indices(answer)
    available = available_indices_from_sources(sources)
    n = chunk_count if chunk_count is not None else len(available)
    return estimate_confidence(
        retrieval_scores=scores_from_sources(sources),
        chunk_count=n,
        cited_indices=cited,
        available_indices=available,
        answer=answer,
        target_k=target_k,
    )


def estimate_for_structured(
    *,
    sources: list[dict] | None,
    items_with_evidence: int,
    total_items: int,
    answer_text: str = "",
    cited_indices: list[int] | set[int] | None = None,
    chunk_count: int | None = None,
    target_k: int = DEFAULT_TARGET_CHUNKS,
) -> ConfidenceResult:
    available = available_indices_from_sources(sources)
    cited = list(cited_indices or extract_cited_indices(answer_text))
    ratio = (
        items_with_evidence / total_items
        if total_items > 0
        else 0.0
    )
    n = chunk_count if chunk_count is not None else len(available)
    return estimate_confidence(
        retrieval_scores=scores_from_sources(sources),
        chunk_count=n,
        cited_indices=cited,
        available_indices=available,
        answer=answer_text,
        structured_evidence_ratio=ratio,
        target_k=target_k,
    )
