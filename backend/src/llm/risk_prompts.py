"""Prompts and checklist specs for AI legal risk highlighting."""

from __future__ import annotations

from src.safety.prompts import with_safety_preamble

RISK_SPECS: list[dict[str, str]] = [
    {
        "id": "automatic_renewal",
        "title": "Automatic renewal",
        "focus": "auto-renew, evergreen, renewal unless notice given",
    },
    {
        "id": "arbitration_clause",
        "title": "Arbitration clause",
        "focus": "binding arbitration, waiver of court/jury trial, dispute forum",
    },
    {
        "id": "unlimited_liability",
        "title": "Unlimited liability",
        "focus": "no liability cap, uncapped damages, carve-outs that remove caps",
    },
    {
        "id": "missing_termination_clause",
        "title": "Missing termination clause",
        "focus": (
            "absence: retrieved excerpts discuss the deal but show no clear "
            "termination / exit / cancellation rights"
        ),
    },
    {
        "id": "missing_payment_terms",
        "title": "Missing payment terms",
        "focus": (
            "absence: retrieved excerpts discuss commercial terms but show no "
            "clear fees, amounts, or payment schedule"
        ),
    },
    {
        "id": "high_penalties",
        "title": "High penalties",
        "focus": "late fees, liquidated damages, harsh penalties, interest, forfeitures",
    },
    {
        "id": "broad_confidentiality",
        "title": "Broad confidentiality",
        "focus": "very broad NDA scope, long duration, one-way confidentiality, residual clauses",
    },
    {
        "id": "one_sided_obligations",
        "title": "One-sided obligations",
        "focus": "duties heavily favor one party; unequal notice, remedies, or termination rights",
    },
]

RISK_SYSTEM_PROMPT = with_safety_preamble(
    """You are a legal risk highlighter for non-lawyers.
Highlight risks as Legal Information from the text — never Legal Advice.

STRICT RULES — never break these:
1. Use ONLY the retrieved document excerpts in DOCUMENT CONTEXT.
2. Never invent risks, clauses, amounts, or parties not supported by the context.
3. Never use outside legal knowledge to fill gaps.
4. Every flagged risk (evidence_found=true) MUST include at least one citation like [Source N]
   matching a Source index in the context, and list those indices in citations.
5. If the context does not clearly support a checklist item, set evidence_found to false,
   explanation to exactly "No evidence found", severity to null, and citations to [].
6. Severity must be one of: "Low", "Medium", "High" when evidence_found is true.
7. Write short plain-language explanations a non-lawyer can understand.
8. Never predict court outcomes or tell the user to sue, settle, or ignore notices.

Special rules for absence risks (missing_termination_clause, missing_payment_terms):
- Flag them ONLY when related commercial/term language appears in the excerpts but the
  termination or payment terms themselves are not present in those excerpts.
- Cite the related excerpts you reviewed (e.g. term/duration language without exit rights).
- If the excerpts are too thin to judge presence or absence, return "No evidence found".

Return ONLY valid JSON with this shape:
{
  "risks": [
    {
      "id": "<risk_id>",
      "title": "<short risk title>",
      "explanation": "<plain language explanation with [Source N] citations, or No evidence found>",
      "severity": "Low" | "Medium" | "High" | null,
      "evidence_found": true|false,
      "citations": [<source index integers>]
    }
  ]
}

Include every risk id listed by the user, in the same order."""
)


def build_risk_human_prompt(filename: str, context: str) -> str:
    lines = "\n".join(
        f"- {spec['id']}: {spec['title']} ({spec['focus']})"
        for spec in RISK_SPECS
    )
    return f"""DOCUMENT FILENAME: {filename}

DOCUMENT CONTEXT (retrieved excerpts only):
{context}

RISK CHECKLIST (analyze each item in this exact order):
{lines}

Produce the JSON object now."""


RISK_RETRIEVAL_QUERIES: list[str] = [
    "automatic renewal evergreen renew unless notice",
    "arbitration dispute resolution mediation jury waiver",
    "liability limit cap unlimited indemnify damages",
    "termination cancel exit notice period end agreement",
    "payment fees price invoice amount schedule due date",
    "penalty late fee liquidated damages interest forfeiture",
    "confidentiality non-disclosure NDA secret information",
    "obligations duties must shall one party only asymmetric",
]
