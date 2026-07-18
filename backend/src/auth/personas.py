"""
User personas (product roles) — distinct from org_role (team permissions).

Stored as stable slugs; display labels are derived for API/UI.
"""

from __future__ import annotations

from typing import Final

# Canonical DB / API values
INDIVIDUAL: Final = "individual"
LAWYER: Final = "lawyer"
CHARTERED_ACCOUNTANT: Final = "chartered_accountant"
BUSINESS_OWNER: Final = "business_owner"
HR_PROFESSIONAL: Final = "hr_professional"
STUDENT: Final = "student"

DEFAULT_ROLE: Final = INDIVIDUAL

ROLE_LABELS: dict[str, str] = {
    INDIVIDUAL: "Individual",
    LAWYER: "Lawyer",
    CHARTERED_ACCOUNTANT: "Chartered Accountant",
    BUSINESS_OWNER: "Business Owner",
    HR_PROFESSIONAL: "HR Professional",
    STUDENT: "Student",
}

ALLOWED_ROLES: frozenset[str] = frozenset(ROLE_LABELS)

# Dashboard welcome copy (also mirrored lightly on the frontend)
ROLE_WELCOME: dict[str, str] = {
    INDIVIDUAL: (
        "Understand your documents, explain contracts in plain language, "
        "detect risks, prepare for consultations, and connect with the "
        "right professionals. Not legal advice."
    ),
    LAWYER: (
        "Review client drafts, explain clauses with citations, compare "
        "agreements, and prepare briefings quickly. Always verify before advising."
    ),
    CHARTERED_ACCOUNTANT: (
        "Understand commercial terms, payment schedules, and "
        "compliance-related language — with citations you can take into review."
    ),
    BUSINESS_OWNER: (
        "Spot obligations, risks, and deadlines in vendor or customer "
        "agreements before you sign — then prepare to talk with counsel."
    ),
    HR_PROFESSIONAL: (
        "Explain employment and policy documents, detect one-sided terms, "
        "and get cited answers for your HR workflows."
    ),
    STUDENT: (
        "Learn how legal documents work — explain contracts, spot risks, "
        "and follow citations back to the source text."
    ),
}


def normalize_role(value: str | None) -> str:
    """Return a valid role slug; fall back to default for legacy/empty values."""
    if not value:
        return DEFAULT_ROLE
    text = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    # Accept display labels case-insensitively
    for slug, label in ROLE_LABELS.items():
        if text == slug or text == label.lower().replace(" ", "_"):
            return slug
    return DEFAULT_ROLE if text not in ALLOWED_ROLES else text


def role_label(role: str | None) -> str:
    slug = normalize_role(role)
    return ROLE_LABELS.get(slug, ROLE_LABELS[DEFAULT_ROLE])


def welcome_message(role: str | None) -> str:
    slug = normalize_role(role)
    return ROLE_WELCOME.get(slug, ROLE_WELCOME[DEFAULT_ROLE])


def is_valid_role(value: str | None) -> bool:
    if not value:
        return False
    text = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if text in ALLOWED_ROLES:
        return True
    return any(text == label.lower().replace(" ", "_") for label in ROLE_LABELS.values())
