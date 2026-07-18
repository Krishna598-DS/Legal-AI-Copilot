# Legal AI Safety Layer

This application distinguishes **Legal Information** from **Legal Advice** and
enforces that distinction in prompts, confidence handling, and output checks.

## Definitions

| Term | Meaning |
|------|---------|
| **Legal Information** | Neutral, document-grounded explanation of what a text says (or does not say), with citations. |
| **Legal Advice** | Recommending actions, predicting outcomes, asserting legal certainty, or substituting for a licensed lawyer. |

The product may provide **Legal Information only**.

## Forbidden behaviors

The AI must never:

- Predict court / tribunal outcomes
- Tell users to sue or file claims
- Tell users to ignore notices or summons
- Claim legal certainty (e.g. “you will win”, “you are definitely liable”)
- Present itself as a replacement for a licensed lawyer

## Implementation

| Layer | Location | Role |
|-------|----------|------|
| Policy constants | `backend/src/safety/policy.py` | Definitions + disclaimer copy |
| System prompt block | `backend/src/safety/prompts.py` | `SAFETY_SYSTEM_BLOCK` / `with_safety_preamble()` |
| Output guardrails | `backend/src/safety/guardrails.py` | Pattern detect + sanitize |
| Low-confidence copy | `backend/src/safety/confidence_messaging.py` | Explain *why* + recommend a professional |

### Prompt coverage (reviewed)

Safety preamble is applied to:

- Conversational Q&A (`conversational_chain.py`)
- Typed prompt templates (`prompt_templates.py`)
- Explain My Document (`explain_prompts.py`)
- Risk highlighting (`risk_prompts.py`)
- Expert category recommendation (`expert_prompts.py`)
- Prepare for Consultation (`consultation_prompts.py`)
- Document compare (`rag_service.py`)

### Runtime enforcement

1. **Before return (ask / stream / compare):** `sanitize_legal_output()` replaces unsafe prose.
2. **Structured features:** `scrub_structured_items()` clears unsafe section/risk text.
3. **Low confidence:** answer is replaced with a message that:
   - states confidence is low,
   - explains which signals were weak (retrieval, chunks, citations, grounding),
   - recommends consulting an appropriate licensed professional,
   - restates that the product is not Legal Advice.

## What this is not

- Not a substitute for jurisdiction-specific compliance review
- Not a guarantee that every model hallucination is caught (patterns + grounding reduce risk)
- Not Legal Advice itself — see `SAFETY_DISCLAIMER` in `policy.py`
