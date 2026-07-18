"""Pure helpers for expert-category recommendation (no LLM / vector deps)."""

from __future__ import annotations

import re
from typing import Any

from src.llm.expert_prompts import CATEGORY_KEYWORDS, EXPERT_CATEGORIES
from src.services.explain_grounding import parse_llm_json

_DEFAULT_CATEGORY = "Civil Lawyer"

# Patterns that look like naming a specific professional — reject category if matched.
_PERSON_LIKE_RE = re.compile(
    r"\b(mr\.|mrs\.|ms\.|dr\.|adv\.|advocate)\s+[A-Z]|"
    r"\b(call|contact|hire)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b|"
    r"@|www\.|\.com\b|\+?\d{7,}",
    re.IGNORECASE,
)

# Presence keywords for lightweight risk signals from retrieved text.
_RISK_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Automatic renewal", ("auto-renew", "automatic renewal", "evergreen", "renews unless")),
    ("Arbitration clause", ("arbitration", "arbitral", "binding arbitration")),
    ("Unlimited liability", ("unlimited liability", "no liability cap", "uncapped liability")),
    ("High penalties", ("liquidated damages", "late fee", "penalty of", "penalties")),
    ("Broad confidentiality", ("confidential information", "non-disclosure", "nda")),
    ("One-sided obligations", ("sole discretion", "without liability", "may terminate at any time")),
    ("Missing termination signals", ("term of this agreement", "shall continue")),
    ("Payment / fee terms", ("payment", "invoice", "fee schedule", "consideration")),
]


def normalize_category(raw: str | None) -> str | None:
    """Map free text to an exact allowed category, or None if unknown."""
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()
    if _PERSON_LIKE_RE.search(text):
        return None
    lowered = text.lower()
    for cat in EXPERT_CATEGORIES:
        if lowered == cat.lower():
            return cat
    # Partial contains (e.g. "a property lawyer" / "property")
    for cat in EXPERT_CATEGORIES:
        if cat.lower() in lowered or lowered in cat.lower():
            return cat
    # Keyword token match
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in lowered for w in words if len(w) > 3):
            # Only if the raw string looks category-like
            if "lawyer" in lowered or "accountant" in lowered or "ca" == lowered:
                return cat
    return None


def score_categories(text: str) -> dict[str, int]:
    """Count keyword hits per category in combined signal text."""
    blob = (text or "").lower()
    scores = {cat: 0 for cat in EXPERT_CATEGORIES}
    for cat, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w in blob:
                scores[cat] += 1
    return scores


def best_category_from_scores(scores: dict[str, int]) -> str:
    if not scores:
        return _DEFAULT_CATEGORY
    best = max(scores.items(), key=lambda kv: (kv[1], kv[0] != _DEFAULT_CATEGORY))
    if best[1] <= 0:
        return _DEFAULT_CATEGORY
    return best[0]


def detect_risk_signals(text: str) -> list[str]:
    """Lightweight risk titles from retrieved text (not a full risk LLM pass)."""
    blob = (text or "").lower()
    found: list[str] = []
    for title, needles in _RISK_KEYWORDS:
        if any(n in blob for n in needles):
            found.append(title)
    return found


def normalize_recommendation(
    parsed: dict[str, Any],
    *,
    fallback_text: str,
) -> dict[str, Any]:
    """
    Ensure a single allowed category and a non-empty reason.
    Never returns a specific professional.
    """
    data = parsed if isinstance(parsed, dict) else {}
    category = normalize_category(data.get("category"))
    if category is None:
        category = best_category_from_scores(score_categories(fallback_text))

    reason = str(data.get("reason") or "").strip()
    # Never surface reasons that name or contact a specific professional.
    if _PERSON_LIKE_RE.search(reason):
        reason = ""
    if not reason:
        reason = (
            f"Based on the uploaded document signals and related context, "
            f"a {category} is the most relevant expert category to consult."
        )

    based_on = data.get("based_on") if isinstance(data.get("based_on"), dict) else {}
    return {
        "category": category,
        "reason": reason,
        "based_on": {
            "document": bool(based_on.get("document", True)),
            "questions": bool(based_on.get("questions", False)),
            "risks": bool(based_on.get("risks", False)),
        },
    }


# Re-export for tests
__all__ = [
    "normalize_category",
    "normalize_recommendation",
    "score_categories",
    "best_category_from_scores",
    "detect_risk_signals",
    "parse_llm_json",
    "_DEFAULT_CATEGORY",
]
