"""Output-side safety checks for Legal Information vs Legal Advice."""

from __future__ import annotations

import re
from typing import NamedTuple

from src.safety.policy import CONSULT_PROFESSIONAL, SAFETY_DISCLAIMER

# Patterns that strongly indicate forbidden Legal Advice / unsafe claims.
_UNSAFE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "predict_court_outcome",
        re.compile(
            r"\b(you will|you'll)\s+(win|lose|prevail|be (found )?liable)\b|"
            r"\b(court|judge|tribunal)\s+will\s+(definitely|certainly|surely)\b|"
            r"\bguaranteed\s+to\s+(win|lose)\b|"
            r"\b(certain|definite)\s+(victory|defeat|liability)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tell_to_sue",
        re.compile(
            r"\b(you should|you must|you need to|i recommend (that )?you)\s+"
            r"(sue|file (a |an )?(lawsuit|suit|claim|complaint)|litigate|take them to court)\b|"
            r"\b(sue|file suit against)\s+(them|him|her|the (other|company|landlord))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "ignore_notices",
        re.compile(
            r"\b(ignore|disregard|throw away|do not (respond|reply|answer))\s+"
            r"(the |any |this )?(notice|summons|subpoena|legal (letter|notice)|court paper)",
            re.IGNORECASE,
        ),
    ),
    (
        "claim_legal_certainty",
        re.compile(
            r"\b(you are (definitely|certainly|absolutely) (liable|not liable|guilty|innocent))\b|"
            r"\b(this (definitely|certainly|absolutely) means you)\b|"
            r"\b(there is no doubt (that )?you)\b|"
            r"\b(100%\s*(sure|certain)\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "replace_lawyer",
        re.compile(
            r"\b(you (do not|don't) need (a |an )?(lawyer|attorney|counsel))\b|"
            r"\b(no need (for|to (hire|consult)) (a |an )?(lawyer|attorney))\b|"
            r"\b(i am your (lawyer|attorney)|acting as your (lawyer|attorney|counsel))\b|"
            r"\b(this (replaces|substitute[sd]? for) (a |an )?(lawyer|attorney|legal advice))\b",
            re.IGNORECASE,
        ),
    ),
]

SAFE_REPLACEMENT = (
    "I can only provide Legal Information grounded in your document — not Legal Advice.\n\n"
    "I cannot predict court outcomes, tell you to sue or ignore notices, claim legal "
    "certainty, or replace a licensed lawyer.\n\n"
    f"{CONSULT_PROFESSIONAL}\n\n"
    f"{SAFETY_DISCLAIMER}"
)


class SafetyFinding(NamedTuple):
    code: str
    excerpt: str


def find_safety_violations(text: str) -> list[SafetyFinding]:
    """Return deterministic safety violations found in model output."""
    if not text:
        return []
    findings: list[SafetyFinding] = []
    for code, pattern in _UNSAFE_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(SafetyFinding(code=code, excerpt=match.group(0)))
    return findings


def is_unsafe_legal_output(text: str) -> bool:
    return bool(find_safety_violations(text))


def sanitize_legal_output(text: str) -> tuple[str, list[str]]:
    """
    If output crosses into Legal Advice / forbidden claims, replace with a safe message.

    Returns (safe_text, violation_codes).
    """
    findings = find_safety_violations(text or "")
    if not findings:
        return text or "", []
    codes = [f.code for f in findings]
    return SAFE_REPLACEMENT, codes


def scrub_structured_content(
    content: str,
    *,
    missing_text: str = "Not found in the retrieved excerpts of this document.",
) -> tuple[str, bool, list[str]]:
    """
    For structured JSON fields: if unsafe, replace with a missing/safe stub.

    Returns (content, was_scrubbed, violation_codes).
    """
    findings = find_safety_violations(content or "")
    if not findings:
        return content or "", False, []
    return missing_text, True, [f.code for f in findings]


def scrub_structured_items(
    items: list[dict],
    *,
    text_keys: tuple[str, ...] = ("content", "explanation"),
    missing_text: str = "Not found in the retrieved excerpts of this document.",
) -> list[str]:
    """
    Scrub unsafe text fields on structured result items in place.

    Returns list of violation codes encountered.
    """
    codes: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in text_keys:
            if key not in item:
                continue
            scrubbed, bad, found = scrub_structured_content(
                str(item.get(key) or ""), missing_text=missing_text
            )
            if bad:
                item[key] = scrubbed
                item["evidence_found"] = False
                if "citations" in item:
                    item["citations"] = []
                if "items" in item:
                    item["items"] = []
                if "severity" in item:
                    item["severity"] = None
                codes.extend(found)
    return codes
