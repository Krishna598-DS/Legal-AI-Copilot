"""Unit tests for deterministic confidence estimation."""

from __future__ import annotations

from src.services.confidence import (
    MEDIUM_RECOMMENDATION,
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
    apply_confidence_policy,
    citation_coverage_factor,
    chunks_factor,
    distance_to_similarity,
    estimate_confidence,
    estimate_for_text_answer,
    grounding_factor,
    level_from_score,
    retrieval_factor,
)


def test_distance_to_similarity_monotonic():
    assert distance_to_similarity(0) == 1.0
    assert distance_to_similarity(1) == 0.5
    assert distance_to_similarity(3) < distance_to_similarity(1)


def test_missing_retrieval_scores_are_zero():
    assert retrieval_factor(None) == 0.0
    assert retrieval_factor([]) == 0.0


def test_chunks_and_citations():
    assert chunks_factor(0) == 0.0
    assert chunks_factor(3, target_k=3) == 1.0
    assert citation_coverage_factor([1, 2], [1, 2, 3]) == 2 / 3
    assert citation_coverage_factor([9], [1, 2]) == 0.0


def test_grounding_rewards_valid_citations():
    g = grounding_factor(
        "Payment is due in 30 days [Source 1].",
        available_indices=[1, 2],
    )
    assert g > 0.5


def test_grounding_not_found_is_low_not_zero():
    g = grounding_factor(
        "This information is not found in the provided document.",
        available_indices=[1],
    )
    assert 0.0 < g < 0.5


def test_levels_and_policy():
    assert level_from_score(THRESHOLD_HIGH) == "High"
    assert level_from_score(THRESHOLD_MEDIUM) == "Medium"
    assert level_from_score(THRESHOLD_MEDIUM - 0.01) == "Low"

    high = estimate_confidence(
        retrieval_scores=[0.9, 0.85],
        chunk_count=4,
        cited_indices=[1, 2],
        available_indices=[1, 2, 3],
        answer="Obligations are mutual [Source 1] [Source 2].",
    )
    assert high.confidence_level in {"High", "Medium"}
    assert apply_confidence_policy("Answer body.", high).startswith("Answer")

    mediumish = estimate_confidence(
        retrieval_scores=[0.55],
        chunk_count=2,
        cited_indices=[1],
        available_indices=[1, 2, 3, 4],
        answer="Some point [Source 1].",
    )
    # Force Medium path for policy check if score lands Medium
    if mediumish.confidence_level == "Medium":
        out = apply_confidence_policy("Draft answer.", mediumish)
        assert MEDIUM_RECOMMENDATION in out

    low = estimate_confidence(
        retrieval_scores=[],
        chunk_count=0,
        cited_indices=[],
        available_indices=[],
        answer="I think the liability is unlimited.",
    )
    assert low.confidence_level == "Low"
    assert low.confidence_score < THRESHOLD_MEDIUM
    abstain = apply_confidence_policy("Invented.", low)
    assert "cannot answer this confidently" in abstain.lower()
    assert "why confidence is low" in abstain.lower()
    assert "legal professional" in abstain.lower()
    assert "Legal Advice" in abstain or "legal advice" in abstain.lower()


def test_never_fabricates_high_without_signals():
    conf = estimate_for_text_answer(
        answer="Clearly the contract auto-renews forever.",
        sources=[],
        chunk_count=0,
    )
    assert conf.confidence_level == "Low"
    assert conf.confidence_score < THRESHOLD_MEDIUM


def test_sources_with_retrieval_score():
    sources = [
        {"index": 1, "retrieval_score": 0.8},
        {"index": 2, "retrieval_score": 0.7},
    ]
    conf = estimate_for_text_answer(
        answer="Auto-renewal applies [Source 1] [Source 2].",
        sources=sources,
        chunk_count=2,
    )
    assert conf.factors["retrieval_score"] > 0.6
    assert conf.factors["citation_coverage"] == 1.0
    assert conf.confidence_score > 0.0
