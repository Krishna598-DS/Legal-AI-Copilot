"""Prompts and section specs for Prepare for Consultation."""

from __future__ import annotations

from src.safety.prompts import with_safety_preamble

CONSULTATION_SECTION_SPECS: list[dict[str, str]] = [
    {
        "id": "summary",
        "title": "Summary",
        "focus": "short plain-language overview of what the document is and covers",
    },
    {
        "id": "important_facts",
        "title": "Important facts",
        "focus": "parties, amounts, subject matter, and other concrete facts stated in the text",
    },
    {
        "id": "timeline",
        "title": "Timeline",
        "focus": "dates, durations, notice periods, renewal and deadline chronology from the text",
    },
    {
        "id": "important_clauses",
        "title": "Important clauses",
        "focus": "key operative clauses (payment, term, termination, liability, etc.) as written",
    },
    {
        "id": "potential_risks",
        "title": "Potential risks",
        "focus": "risks explicitly supported by the excerpts (penalties, one-sided terms, caps, etc.)",
    },
    {
        "id": "questions_for_lawyer",
        "title": "Questions to ask the lawyer",
        "focus": (
            "clarifying questions tied to specific clauses or gaps in the excerpts; "
            "each question must relate to cited document content — not general legal advice"
        ),
    },
    {
        "id": "documents_to_carry",
        "title": "Documents to carry",
        "focus": (
            "this uploaded file plus any schedules/annexures/exhibits the excerpts say are attached "
            "or incorporated — never invent personal IDs or unrelated paperwork"
        ),
    },
]

CONSULTATION_SYSTEM_PROMPT = with_safety_preamble(
    """You prepare a consultation briefing packet for a non-lawyer.
This is Legal Information to help them prepare — never Legal Advice.

STRICT RULES — never break these:
1. Use ONLY the retrieved document excerpts in DOCUMENT CONTEXT.
2. Summarize document contents only. Never give legal advice, strategy, or opinions about what the user should do.
3. Never invent parties, dates, amounts, clauses, risks, or documents not supported by the context.
4. Every factual claim MUST include at least one citation like [Source N] matching a Source index.
5. If a section is not supported, set evidence_found to false and content to exactly:
   "Not found in the retrieved excerpts of this document."
6. For questions_for_lawyer: only ask clarifying questions about what the document says or leaves unclear,
   each tied to citations. Do not advise outcomes or predict what counsel will say.
7. For documents_to_carry: include the uploaded filename and only attachments/schedules named in the excerpts.
8. Write plain language. Never tell the user to sue or ignore notices.

Return ONLY valid JSON:
{
  "sections": [
    {
      "id": "<section_id>",
      "content": "<plain text; use newline bullets where helpful; include [Source N]>",
      "items": ["optional bullet strings with [Source N]"],
      "evidence_found": true|false,
      "citations": [<source index integers>]
    }
  ]
}

Include every section id listed by the user, in the same order.
If evidence_found is false, citations must be [] and items must be []."""
)


def build_consultation_human_prompt(filename: str, context: str) -> str:
    lines = "\n".join(
        f"- {spec['id']}: {spec['title']} ({spec['focus']})"
        for spec in CONSULTATION_SECTION_SPECS
    )
    return f"""DOCUMENT FILENAME: {filename}

DOCUMENT CONTEXT (retrieved excerpts only):
{context}

SECTIONS TO FILL (in this exact order):
{lines}

Produce the JSON object now. Remember: summarize only — no legal advice."""


CONSULTATION_RETRIEVAL_QUERIES: list[str] = [
    "What type of document or agreement is this and what does it cover?",
    "Who are the parties and what are the key facts and amounts?",
    "What dates, deadlines, term, notice periods, and timeline apply?",
    "What are the important clauses for payment, liability, termination, and confidentiality?",
    "What risks, penalties, one-sided terms, or liability exposure appear?",
    "What schedules, annexures, exhibits, or attachments are referenced?",
    "What obligations and unclear terms might need clarification?",
]
