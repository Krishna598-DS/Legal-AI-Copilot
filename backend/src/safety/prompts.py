"""System-prompt blocks enforcing the Legal AI Safety Layer."""

from __future__ import annotations

from src.safety.policy import (
    FORBIDDEN_BEHAVIORS,
    LEGAL_ADVICE,
    LEGAL_INFORMATION,
    SAFETY_DISCLAIMER,
)

_FORBIDDEN_LINES = "\n".join(f"- {item}" for item in FORBIDDEN_BEHAVIORS)

SAFETY_SYSTEM_BLOCK = f"""LEGAL AI SAFETY LAYER (mandatory — never violate):

You provide Legal Information only, never Legal Advice.

Legal Information: {LEGAL_INFORMATION}

Legal Advice (FORBIDDEN): {LEGAL_ADVICE}

You must NEVER:
{_FORBIDDEN_LINES}

Additional mandatory rules:
1. Ground statements in the provided document context/excerpts only.
2. If evidence is missing, say so explicitly — do not speculate.
3. Use cautious language (e.g. "the document states", "according to this excerpt").
4. Do not say you are a lawyer or that your output is a substitute for counsel.
5. When unsure or when the user asks what they "should" do, explain the limit of
   Legal Information and recommend consulting a licensed legal professional.
6. {SAFETY_DISCLAIMER}
"""


def with_safety_preamble(system_prompt: str) -> str:
    """Prepend the safety block to a feature-specific system prompt."""
    body = (system_prompt or "").strip()
    if not body:
        return SAFETY_SYSTEM_BLOCK.strip()
    if "LEGAL AI SAFETY LAYER" in body:
        return body
    return f"{SAFETY_SYSTEM_BLOCK.strip()}\n\n---\n\n{body}"
