"""Unit tests for legal risk highlighting grounding (no live OpenAI)."""

from __future__ import annotations

from src.llm.risk_prompts import RISK_SPECS, build_risk_human_prompt
from src.services.explain_grounding import parse_llm_json
from src.services.risk_grounding import (
    _NO_EVIDENCE,
    format_risks_for_chat,
    normalize_risks,
)


def test_parse_risk_json():
    raw = '```json\n{"risks": [{"id": "arbitration_clause", "explanation": "x", "evidence_found": false}]}\n```'
    data = parse_llm_json(raw)
    assert data["risks"][0]["id"] == "arbitration_clause"


def test_normalize_keeps_grounded_risk():
    sources = [
        {
            "index": 1,
            "page": 4,
            "filename": "a.pdf",
            "snippet": "binding arbitration",
            "document_id": "d",
        }
    ]
    parsed = {
        "risks": [
            {
                "id": "arbitration_clause",
                "title": "Arbitration clause",
                "explanation": "Disputes go to binding arbitration [Source 1].",
                "severity": "High",
                "evidence_found": True,
                "citations": [1],
            }
        ]
    }
    risks = normalize_risks(parsed, sources)
    assert len(risks) == len(RISK_SPECS)
    arb = next(r for r in risks if r["id"] == "arbitration_clause")
    assert arb["evidence_found"] is True
    assert arb["severity"] == "High"
    assert arb["citations"][0]["page"] == 4


def test_normalize_rejects_uncited_risk():
    sources = [
        {
            "index": 1,
            "page": 1,
            "filename": "a.pdf",
            "snippet": "x",
            "document_id": "d",
        }
    ]
    parsed = {
        "risks": [
            {
                "id": "unlimited_liability",
                "title": "Unlimited liability",
                "explanation": "There is no liability cap.",
                "severity": "High",
                "evidence_found": True,
                "citations": [],
            }
        ]
    }
    risks = normalize_risks(parsed, sources)
    item = next(r for r in risks if r["id"] == "unlimited_liability")
    assert item["evidence_found"] is False
    assert item["explanation"] == _NO_EVIDENCE
    assert item["severity"] is None


def test_normalize_rejects_invalid_severity():
    sources = [
        {
            "index": 2,
            "page": 2,
            "filename": "a.pdf",
            "snippet": "renew",
            "document_id": "d",
        }
    ]
    parsed = {
        "risks": [
            {
                "id": "automatic_renewal",
                "explanation": "Auto renews [Source 2]",
                "severity": "Critical",
                "evidence_found": True,
                "citations": [2],
            }
        ]
    }
    risks = normalize_risks(parsed, sources)
    item = next(r for r in risks if r["id"] == "automatic_renewal")
    assert item["explanation"] == _NO_EVIDENCE


def test_normalize_sorts_by_severity():
    sources = [
        {"index": 1, "page": 1, "filename": "a.pdf", "snippet": "a", "document_id": "d"},
        {"index": 2, "page": 2, "filename": "a.pdf", "snippet": "b", "document_id": "d"},
    ]
    parsed = {
        "risks": [
            {
                "id": "broad_confidentiality",
                "explanation": "Broad NDA [Source 1]",
                "severity": "Low",
                "evidence_found": True,
                "citations": [1],
            },
            {
                "id": "high_penalties",
                "explanation": "Harsh late fee [Source 2]",
                "severity": "High",
                "evidence_found": True,
                "citations": [2],
            },
        ]
    }
    risks = normalize_risks(parsed, sources)
    flagged = [r for r in risks if r["evidence_found"]]
    assert flagged[0]["id"] == "high_penalties"
    assert flagged[1]["id"] == "broad_confidentiality"


def test_empty_parse_fills_checklist():
    risks = normalize_risks({}, [])
    assert [r["id"] for r in risks] == [s["id"] for s in RISK_SPECS]
    assert all(r["explanation"] == _NO_EVIDENCE for r in risks)


def test_build_risk_human_prompt():
    prompt = build_risk_human_prompt("msa.pdf", "[Source 1] hi")
    assert "msa.pdf" in prompt
    assert "automatic_renewal" in prompt
    assert "[Source 1] hi" in prompt


def test_format_risks_for_chat():
    text = format_risks_for_chat(
        [
            {
                "title": "Arbitration clause",
                "severity": "High",
                "explanation": "Binding arb [Source 1]",
                "citations": [{"index": 1, "page": 5}],
            }
        ]
    )
    assert "Legal Risk Highlights" in text
    assert "High" in text
    assert "Source 1 p.5" in text
