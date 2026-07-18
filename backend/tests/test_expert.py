"""Unit tests for expert-category recommendation grounding."""

from __future__ import annotations

from src.llm.expert_prompts import EXPERT_CATEGORIES, build_expert_human_prompt
from src.services.expert_grounding import (
    _DEFAULT_CATEGORY,
    best_category_from_scores,
    detect_risk_signals,
    normalize_category,
    normalize_recommendation,
    score_categories,
)


def test_categories_catalog():
    assert "Property Lawyer" in EXPERT_CATEGORIES
    assert "Chartered Accountant" in EXPERT_CATEGORIES
    assert len(EXPERT_CATEGORIES) == 8


def test_normalize_category_exact_and_fuzzy():
    assert normalize_category("Property Lawyer") == "Property Lawyer"
    assert normalize_category("property lawyer") == "Property Lawyer"
    assert normalize_category("Mr. John Smith Esq.") is None


def test_score_property_document():
    text = "This lease concerns property ownership and transfer of the premises."
    scores = score_categories(text)
    assert best_category_from_scores(scores) == "Property Lawyer"


def test_score_employment():
    text = "Employee offer letter with salary, workplace duties, and non-compete."
    assert best_category_from_scores(score_categories(text)) == "Employment Lawyer"


def test_normalize_recommendation_whitelist():
    out = normalize_recommendation(
        {
            "category": "Hire Attorney Jane Doe at Acme Law",
            "reason": "Call Jane Doe at +15551212 for help.",
            "based_on": {"document": True, "questions": False, "risks": True},
        },
        fallback_text="shareholder merger corporation board directors",
    )
    assert out["category"] in EXPERT_CATEGORIES
    assert out["category"] == "Corporate Lawyer"
    assert "Jane Doe" not in out["reason"]
    assert "+15551212" not in out["reason"]


def test_normalize_falls_back_to_default():
    out = normalize_recommendation({}, fallback_text="")
    assert out["category"] == _DEFAULT_CATEGORY
    assert out["reason"]


def test_detect_risk_signals():
    text = "Disputes shall be resolved by binding arbitration. The contract auto-renews."
    risks = detect_risk_signals(text)
    assert "Arbitration clause" in risks
    assert "Automatic renewal" in risks


def test_build_prompt_includes_inputs():
    prompt = build_expert_human_prompt(
        filename="lease.pdf",
        context="[Source 1] property lease",
        questions=["Who owns the land?"],
        detected_risks=["Automatic renewal"],
    )
    assert "lease.pdf" in prompt
    assert "Property Lawyer" in prompt
    assert "Who owns the land?" in prompt
    assert "Automatic renewal" in prompt
