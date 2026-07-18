"""Prompts and section specs for Explain My Document."""

from __future__ import annotations

from src.safety.prompts import with_safety_preamble

EXPLAIN_SECTION_SPECS: list[dict[str, str]] = [
    {
        "id": "what_this_document_is",
        "title": "What this document is",
        "focus": "document type / title / nature of the agreement",
    },
    {
        "id": "parties",
        "title": "Parties involved",
        "focus": "who the parties are and their roles",
    },
    {
        "id": "purpose",
        "title": "Purpose",
        "focus": "why the document exists / what deal or relationship it creates",
    },
    {
        "id": "important_dates",
        "title": "Important dates",
        "focus": "effective date, term, start/end dates, renewal dates",
    },
    {
        "id": "important_obligations",
        "title": "Important obligations",
        "focus": "key duties each party must perform",
    },
    {
        "id": "key_clauses",
        "title": "Key clauses",
        "focus": "payment, liability, termination, confidentiality, IP, governing law, etc.",
    },
    {
        "id": "potential_risks",
        "title": "Potential risks",
        "focus": "penalties, one-sided terms, liability exposure, termination risks explicitly in the text",
    },
    {
        "id": "important_deadlines",
        "title": "Important deadlines",
        "focus": "notice periods, payment due dates, delivery deadlines, renewal/cancellation windows",
    },
]

EXPLAIN_SYSTEM_PROMPT = with_safety_preamble(
    """You are a plain-language legal document explainer for non-lawyers.
Provide Legal Information about what the document says — never Legal Advice.

STRICT RULES — never break these:
1. Use ONLY the retrieved document excerpts in DOCUMENT CONTEXT.
2. Never invent parties, dates, amounts, obligations, risks, or clauses.
3. Never use outside legal knowledge to fill gaps.
4. Every factual claim MUST include at least one citation like [Source N] matching a Source index in the context.
5. If the context does not clearly support a section, set evidence_found to false and content to exactly:
   "Not found in the retrieved excerpts of this document."
6. Write short, simple sentences a non-lawyer can understand.
7. Do not tell the user what to do, whether to sue, or how a court would decide.

Return ONLY valid JSON with this shape:
{
  "sections": [
    {
      "id": "<section_id>",
      "content": "<plain language text with [Source N] citations>",
      "evidence_found": true|false,
      "citations": [<source index integers>]
    }
  ]
}

Include every section id listed by the user, in the same order.
citations must be integers that appear as [Source N] in DOCUMENT CONTEXT.
If evidence_found is false, citations must be []."""
)


def build_explain_human_prompt(filename: str, context: str) -> str:
    section_lines = "\n".join(
        f"- {spec['id']}: {spec['title']} ({spec['focus']})"
        for spec in EXPLAIN_SECTION_SPECS
    )
    return f"""DOCUMENT FILENAME: {filename}

DOCUMENT CONTEXT (retrieved excerpts only):
{context}

SECTIONS TO FILL (in this exact order):
{section_lines}

Produce the JSON object now."""


# Multi-query retrieval topics to cover all explanation sections.
EXPLAIN_RETRIEVAL_QUERIES: list[str] = [
    "What type of document or agreement is this and what is its title?",
    "Who are the parties to this agreement and what are their roles?",
    "What is the purpose or subject matter of this document?",
    "What are the important dates, effective date, term, and duration?",
    "What are the main obligations and duties of each party?",
    "What are the key clauses including payment, liability, termination, and confidentiality?",
    "What risks, penalties, liabilities, or one-sided terms are stated?",
    "What deadlines, notice periods, payment due dates, or time limits apply?",
]
