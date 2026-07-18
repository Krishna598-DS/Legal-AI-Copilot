"""Unit tests for Prepare for Consultation grounding + PDF (no live OpenAI)."""

from __future__ import annotations

from src.llm.consultation_prompts import (
    CONSULTATION_SECTION_SPECS,
    build_consultation_human_prompt,
)
from src.services.consultation_grounding import (
    _MISSING,
    format_consultation_for_chat,
    normalize_consultation_sections,
)
from src.services.consultation_pdf import build_consultation_pdf
from src.services.explain_grounding import parse_llm_json


def test_parse_consultation_json():
    raw = '```json\n{"sections": [{"id": "summary", "content": "x", "evidence_found": false}]}\n```'
    assert parse_llm_json(raw)["sections"][0]["id"] == "summary"


def test_normalize_requires_citations():
    sources = [
        {
            "index": 1,
            "page": 2,
            "filename": "lease.pdf",
            "snippet": "lease of property",
            "document_id": "d",
        }
    ]
    parsed = {
        "sections": [
            {
                "id": "summary",
                "content": "This is a lease [Source 1].",
                "evidence_found": True,
                "citations": [1],
            },
            {
                "id": "timeline",
                "content": "Starts tomorrow — invented",
                "evidence_found": True,
                "citations": [],
            },
        ]
    }
    secs = normalize_consultation_sections(
        parsed, sources, uploaded_filename="lease.pdf"
    )
    assert len(secs) == len(CONSULTATION_SECTION_SPECS)
    summary = next(s for s in secs if s["id"] == "summary")
    assert summary["evidence_found"] is True
    timeline = next(s for s in secs if s["id"] == "timeline")
    assert timeline["content"] == _MISSING
    carry = next(s for s in secs if s["id"] == "documents_to_carry")
    assert "lease.pdf" in carry["content"]


def test_rejects_advice_like_content():
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
                "id": "potential_risks",
                "content": "You should sue immediately [Source 1].",
                "evidence_found": True,
                "citations": [1],
            }
        ]
    }
    secs = normalize_consultation_sections(
        parsed, sources, uploaded_filename="a.pdf"
    )
    risk = next(s for s in secs if s["id"] == "potential_risks")
    assert risk["evidence_found"] is False
    assert risk["content"] == _MISSING


def test_build_prompt_lists_sections():
    prompt = build_consultation_human_prompt("nda.pdf", "[Source 1] hi")
    assert "questions_for_lawyer" in prompt
    assert "documents_to_carry" in prompt
    assert "nda.pdf" in prompt


def test_format_chat_includes_disclaimer():
    text = format_consultation_for_chat(
        [
            {
                "title": "Summary",
                "content": "An NDA [Source 1]",
                "citations": [{"index": 1, "page": 1}],
            }
        ]
    )
    assert "Prepare for Consultation" in text
    assert "not legal advice" in text.lower()


def test_pdf_builds_valid_header():
    sections = [
        {
            "title": "Summary",
            "content": "Lease agreement [Source 1]",
            "citations": [{"index": 1, "page": 3}],
        },
        {
            "title": "Important facts",
            "content": "Not found in the retrieved excerpts of this document.",
            "citations": [],
        },
    ]
    pdf = build_consultation_pdf(filename="lease.pdf", sections=sections)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 200
