"""Human-readable explanations when confidence is low or medium."""

from __future__ import annotations

from typing import Any

from src.safety.policy import CONSULT_PROFESSIONAL, SAFETY_DISCLAIMER


def explain_confidence_factors(factors: dict[str, float] | None) -> list[str]:
    """Explain which measured signals were weak (never fabricated)."""
    f = factors or {}
    reasons: list[str] = []
    if f.get("retrieval_score", 0) < 0.4:
        reasons.append(
            "retrieved excerpts were only weakly related to the question (low retrieval score)"
        )
    if f.get("supporting_chunks", 0) < 0.5:
        reasons.append("few supporting document chunks were available")
    if f.get("citation_coverage", 0) < 0.4:
        reasons.append("the answer was not well covered by source citations")
    if f.get("answer_grounding", 0) < 0.4:
        reasons.append("the answer was not sufficiently grounded in cited excerpts")
    if not reasons:
        reasons.append(
            "overall confidence signals did not meet the threshold for a reliable answer"
        )
    return reasons


def build_low_confidence_message(
    factors: dict[str, float] | None = None,
    *,
    expert_category: str | None = None,
) -> str:
    reasons = explain_confidence_factors(factors)
    reason_text = "; ".join(reasons)
    expert_bit = ""
    if expert_category:
        expert_bit = (
            f" Consider consulting a licensed {expert_category} "
            "about your situation."
        )
    else:
        expert_bit = f" {CONSULT_PROFESSIONAL}"

    return (
        "I cannot answer this confidently based on the retrieved document excerpts.\n\n"
        f"Why confidence is low: {reason_text}.\n\n"
        "This tool provides Legal Information about documents, not Legal Advice, "
        "and does not replace a licensed lawyer."
        f"{expert_bit}\n\n"
        f"{SAFETY_DISCLAIMER}"
    )


def build_medium_confidence_note() -> str:
    return (
        "Confidence: Medium — This is Legal Information only, not Legal Advice. "
        "Optional review by a qualified legal professional is recommended before "
        "relying on this."
    )
