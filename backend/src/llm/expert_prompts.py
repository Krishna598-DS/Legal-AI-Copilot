"""Prompts and category catalog for expert recommendation (categories only)."""

from __future__ import annotations

from src.safety.prompts import with_safety_preamble

EXPERT_CATEGORIES: list[str] = [
    "Property Lawyer",
    "Family Lawyer",
    "Corporate Lawyer",
    "Criminal Lawyer",
    "Civil Lawyer",
    "Employment Lawyer",
    "Tax Lawyer",
    "Chartered Accountant",
]

# Keyword hints used for deterministic signals / fallback (not shown as named people).
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Property Lawyer": [
        "property", "real estate", "lease", "landlord", "tenant", "deed",
        "mortgage", "conveyance", "title", "premises", "rent", "easement",
        "sale of land", "apartment", "plot",
    ],
    "Family Lawyer": [
        "divorce", "custody", "marriage", "spouse", "matrimonial", "alimony",
        "maintenance", "child support", "prenup", "separation", "adoption",
        "domestic",
    ],
    "Corporate Lawyer": [
        "shareholder", "board", "merger", "acquisition", "incorporation",
        "company", "corporation", "equity", "securities", "joint venture",
        "articles of association", "bylaws", "director", "msa", "saas",
        "vendor agreement", "service agreement", "nda",
    ],
    "Criminal Lawyer": [
        "criminal", "prosecution", "felony", "misdemeanor", "bail",
        "arrest", "charge", "offense", "penal", "police", "accused",
    ],
    "Civil Lawyer": [
        "civil suit", "damages", "injunction", "tort", "negligence",
        "dispute", "plaintiff", "defendant", "settlement", "claim",
    ],
    "Employment Lawyer": [
        "employment", "employee", "employer", "workplace", "salary",
        "wages", "termination of employment", "non-compete", "severance",
        "hr policy", "offer letter", "wrongful dismissal", "labour", "labor",
    ],
    "Tax Lawyer": [
        "tax", "gst", "vat", "withholding", "income tax", "capital gains",
        "tax assessment", "tax liability", "customs duty",
    ],
    "Chartered Accountant": [
        "audit", "accounting", "financial statements", "bookkeeping",
        "balance sheet", "invoice", "accounts payable", "accounts receivable",
        "statutory audit", "ca firm", "chartered accountant",
    ],
}

EXPERT_RETRIEVAL_QUERIES: list[str] = [
    "What type of agreement or legal document is this?",
    "property lease land real estate ownership transfer",
    "employment employee employer workplace salary",
    "company shareholder merger corporate commercial contract",
    "tax GST accounting audit financial",
    "family divorce custody marriage matrimonial",
    "criminal offense prosecution charge",
    "civil dispute damages claim litigation",
]

EXPERT_SYSTEM_PROMPT = with_safety_preamble(
    """You are an expert-category recommender for a legal document copilot.
Recommend a category so the user can find appropriate licensed help — this is not Legal Advice.

STRICT RULES:
1. Recommend exactly ONE category from the allowed list. Never invent new categories.
2. Never recommend a specific person, firm, phone number, or named professional.
3. Base the recommendation only on: document excerpts, user questions, and detected risk signals provided.
4. Do not use outside knowledge about the user's situation beyond the provided signals.
5. Explain the reason in plain language for a non-lawyer.
6. If signals are weak or mixed, pick the single best-fit category and say the evidence is limited.
7. This is not a referral guaranteeing a particular professional and does not replace counsel.
8. Do not predict outcomes or tell the user whether to sue.

Return ONLY valid JSON:
{
  "category": "<exact category from the allowed list>",
  "reason": "<1-3 sentences explaining why this category fits>",
  "based_on": {
    "document": true|false,
    "questions": true|false,
    "risks": true|false
  }
}"""
)


def build_expert_human_prompt(
    *,
    filename: str,
    context: str,
    questions: list[str],
    detected_risks: list[str],
) -> str:
    cats = "\n".join(f"- {c}" for c in EXPERT_CATEGORIES)
    q_block = "\n".join(f"- {q}" for q in questions) if questions else "(none yet)"
    r_block = (
        "\n".join(f"- {r}" for r in detected_risks) if detected_risks else "(none detected)"
    )
    return f"""DOCUMENT FILENAME: {filename}

DOCUMENT EXCERPTS (retrieved):
{context}

RECENT USER QUESTIONS:
{q_block}

DETECTED RISK SIGNALS:
{r_block}

ALLOWED CATEGORIES (pick exactly one):
{cats}

Produce the JSON object now."""
