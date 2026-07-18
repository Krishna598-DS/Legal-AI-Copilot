"""Tests for the Legal AI Safety Layer."""

from __future__ import annotations

from src.llm.explain_prompts import EXPLAIN_SYSTEM_PROMPT
from src.llm.expert_prompts import EXPERT_SYSTEM_PROMPT
from src.llm.risk_prompts import RISK_SYSTEM_PROMPT
from src.llm.consultation_prompts import CONSULTATION_SYSTEM_PROMPT
from src.safety.confidence_messaging import build_low_confidence_message
from src.safety.guardrails import (
    find_safety_violations,
    is_unsafe_legal_output,
    sanitize_legal_output,
    scrub_structured_items,
)
from src.safety.policy import FORBIDDEN_BEHAVIORS, LEGAL_ADVICE, LEGAL_INFORMATION
from src.safety.prompts import SAFETY_SYSTEM_BLOCK, with_safety_preamble


def test_policy_distinguishes_information_and_advice():
    assert "document-grounded" in LEGAL_INFORMATION.lower() or "document" in LEGAL_INFORMATION.lower()
    assert "recommend" in LEGAL_ADVICE.lower() or "predict" in LEGAL_ADVICE.lower()
    assert len(FORBIDDEN_BEHAVIORS) >= 5


def test_safety_block_in_feature_prompts():
    assert "LEGAL AI SAFETY LAYER" in SAFETY_SYSTEM_BLOCK
    for prompt in (
        EXPLAIN_SYSTEM_PROMPT,
        RISK_SYSTEM_PROMPT,
        EXPERT_SYSTEM_PROMPT,
        CONSULTATION_SYSTEM_PROMPT,
    ):
        assert "LEGAL AI SAFETY LAYER" in prompt
        assert "Legal Advice" in prompt or "legal advice" in prompt.lower()
    wrapped = with_safety_preamble("Feature rules here.")
    assert "LEGAL AI SAFETY LAYER" in wrapped
    # Idempotent
    assert with_safety_preamble(wrapped) == wrapped


def test_detects_forbidden_advice():
    cases = [
        ("tell_to_sue", "You should sue them immediately for breach."),
        ("ignore_notices", "You can ignore the notice from the landlord."),
        ("predict_court_outcome", "You will win in court for sure."),
        ("claim_legal_certainty", "You are definitely liable under this clause."),
        ("replace_lawyer", "You don't need a lawyer for this."),
    ]
    for code, text in cases:
        findings = find_safety_violations(text)
        assert findings, text
        assert any(f.code == code for f in findings), (code, findings)


def test_safe_document_summary_passes():
    text = (
        "According to the agreement, rent is due on the first of each month [Source 1]. "
        "This information is not found in the provided document for late fees."
    )
    assert not is_unsafe_legal_output(text)
    safe, codes = sanitize_legal_output(text)
    assert codes == []
    assert safe == text


def test_sanitize_replaces_unsafe_output():
    unsafe = "I recommend that you sue the other party next week."
    safe, codes = sanitize_legal_output(unsafe)
    assert "tell_to_sue" in codes
    assert "Legal Information" in safe
    assert "licensed" in safe.lower()


def test_scrub_structured_items():
    sections = [
        {
            "id": "summary",
            "content": "You should sue them [Source 1].",
            "evidence_found": True,
            "citations": [{"index": 1}],
        }
    ]
    codes = scrub_structured_items(sections, text_keys=("content",))
    assert codes
    assert sections[0]["evidence_found"] is False
    assert "Not found" in sections[0]["content"]


def test_low_confidence_explains_why():
    msg = build_low_confidence_message(
        {
            "retrieval_score": 0.1,
            "supporting_chunks": 0.2,
            "citation_coverage": 0.0,
            "answer_grounding": 0.1,
        }
    )
    assert "Why confidence is low" in msg
    assert "retrieval" in msg.lower()
    assert "licensed legal professional" in msg.lower()
    assert "Legal Advice" in msg or "legal advice" in msg.lower()
