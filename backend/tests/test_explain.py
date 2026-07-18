"""Unit tests for Explain My Document grounding (no live OpenAI)."""

from __future__ import annotations

from src.llm.explain_prompts import EXPLAIN_SECTION_SPECS, build_explain_human_prompt
from src.services.explain_grounding import (
    _MISSING,
    extract_citation_indices,
    format_explanation_for_chat,
    normalize_sections,
    parse_llm_json,
)


def test_parse_llm_json_fenced():
    raw = '```json\n{"sections": [{"id": "parties", "content": "A", "evidence_found": false, "citations": []}]}\n```'
    data = parse_llm_json(raw)
    assert "sections" in data
    assert data["sections"][0]["id"] == "parties"


def test_parse_llm_json_embedded():
    raw = 'Here you go:\n{"sections": []}\nThanks'
    assert parse_llm_json(raw) == {"sections": []}


def test_extract_citation_indices():
    assert extract_citation_indices("A [Source 2] and [Source 1] and [Source 2]") == [
        2,
        1,
    ]


def test_normalize_downgrades_uncited_claims():
    sources = [
        {
            "index": 1,
            "page": 2,
            "filename": "a.pdf",
            "snippet": "x",
            "document_id": "d",
        }
    ]
    parsed = {
        "sections": [
            {
                "id": "parties",
                "content": "Alice and Bob [Source 1]",
                "evidence_found": True,
                "citations": [1],
            },
            {
                "id": "important_dates",
                "content": "Tomorrow — invented",
                "evidence_found": True,
                "citations": [],
            },
        ]
    }
    secs = normalize_sections(parsed, sources)
    assert len(secs) == len(EXPLAIN_SECTION_SPECS)
    parties = next(s for s in secs if s["id"] == "parties")
    assert parties["evidence_found"] is True
    assert parties["citations"][0]["index"] == 1
    dates = next(s for s in secs if s["id"] == "important_dates")
    assert dates["evidence_found"] is False
    assert dates["content"] == _MISSING
    assert dates["citations"] == []


def test_normalize_fills_missing_sections():
    secs = normalize_sections({}, [])
    assert [s["id"] for s in secs] == [s["id"] for s in EXPLAIN_SECTION_SPECS]
    assert all(s["content"] == _MISSING for s in secs)
    assert all(s["evidence_found"] is False for s in secs)


def test_normalize_rejects_unknown_source_index():
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
        "sections": [
            {
                "id": "purpose",
                "content": "Lease [Source 9]",
                "evidence_found": True,
                "citations": [9],
            }
        ]
    }
    secs = normalize_sections(parsed, sources)
    purpose = next(s for s in secs if s["id"] == "purpose")
    assert purpose["evidence_found"] is False
    assert purpose["content"] == _MISSING


def test_build_explain_human_prompt_lists_sections():
    prompt = build_explain_human_prompt("nda.pdf", "[Source 1] hello")
    assert "nda.pdf" in prompt
    assert "parties" in prompt
    assert "[Source 1] hello" in prompt


def test_format_explanation_for_chat():
    text = format_explanation_for_chat(
        [
            {
                "title": "Parties involved",
                "content": "A and B [Source 1]",
                "citations": [{"index": 1, "page": 3}],
            }
        ]
    )
    assert "Explain My Document" in text
    assert "Parties involved" in text
    assert "Source 1 p.3" in text
