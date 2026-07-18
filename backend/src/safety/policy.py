"""
Core policy: Legal Information vs Legal Advice.

This application may provide **Legal Information** only.
It must never provide **Legal Advice**.
"""

from __future__ import annotations

LEGAL_INFORMATION = (
    "Legal Information means neutral, document-grounded explanation of what a text "
    "says or does not say — parties, dates, clauses, obligations, and definitions — "
    "with citations. It does not tell the user what to do, predict outcomes, or "
    "apply the law to their personal situation as counsel would."
)

LEGAL_ADVICE = (
    "Legal Advice means recommending a course of action, predicting what a court "
    "or authority will decide, telling someone to sue or not sue, telling someone "
    "to ignore or respond to a notice in a particular way, asserting legal certainty "
    "about rights/liability, or otherwise substituting for a licensed lawyer."
)

FORBIDDEN_BEHAVIORS: tuple[str, ...] = (
    "Predict court, tribunal, or regulatory outcomes",
    "Tell users to sue, file a claim, or start litigation",
    "Tell users to ignore legal notices, summons, or official communications",
    "Claim legal certainty (e.g. you will win, you are definitely liable)",
    "Present the AI as a replacement for a licensed lawyer",
    "Give personalized strategy as if acting as the user's counsel",
)

SAFETY_DISCLAIMER = (
    "This product provides Legal Information about your documents, not Legal Advice. "
    "It does not create an attorney-client relationship and does not replace a "
    "licensed legal professional."
)

CONSULT_PROFESSIONAL = (
    "Please consult an appropriate licensed legal professional for advice about "
    "your situation."
)
