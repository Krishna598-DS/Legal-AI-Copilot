"""Pure grounding helpers for Prepare for Consultation."""

from __future__ import annotations

from typing import Any

from src.llm.consultation_prompts import CONSULTATION_SECTION_SPECS
from src.services.explain_grounding import (
    extract_citation_indices,
    parse_llm_json,
)

from src.safety.guardrails import is_unsafe_legal_output

_MISSING = "Not found in the retrieved excerpts of this document."
_ADVICE_MARKERS = (
    "you should",
    "you must sue",
    "i recommend that you",
    "this is legal advice",
    "you are entitled to win",
)


def _citation_objects(
    indices: list[int], sources: list[dict]
) -> list[dict[str, Any]]:
    by_index = {
        int(s["index"]): s for s in sources if s.get("index") is not None
    }
    cites: list[dict[str, Any]] = []
    for idx in indices:
        src = by_index.get(idx)
        if not src:
            continue
        cites.append(
            {
                "index": idx,
                "page": src.get("page"),
                "filename": src.get("filename"),
                "snippet": src.get("snippet"),
                "document_id": src.get("document_id"),
            }
        )
    return cites


def _merge_indices(
    explicit: list[int], from_text: list[int], valid: set[int]
) -> list[int]:
    merged: list[int] = []
    seen: set[int] = set()
    for idx in explicit + from_text:
        if idx in valid and idx not in seen:
            seen.add(idx)
            merged.append(idx)
    return merged


def _looks_like_advice(text: str) -> bool:
    if is_unsafe_legal_output(text or ""):
        return True
    lower = (text or "").lower()
    return any(p in lower for p in _ADVICE_MARKERS)


def _missing_section(spec: dict[str, str]) -> dict[str, Any]:
    return {
        "id": spec["id"],
        "title": spec["title"],
        "content": _MISSING,
        "items": [],
        "evidence_found": False,
        "citations": [],
    }


def normalize_consultation_sections(
    parsed: dict[str, Any],
    sources: list[dict],
    *,
    uploaded_filename: str | None = None,
) -> list[dict[str, Any]]:
    """
    Ensure all prep sections exist; drop uncited or advice-like claims.
    """
    valid_indices = {
        int(s["index"]) for s in sources if s.get("index") is not None
    }
    by_id: dict[str, dict] = {}
    raw_sections = parsed.get("sections") if isinstance(parsed, dict) else None
    if isinstance(raw_sections, list):
        for item in raw_sections:
            if isinstance(item, dict) and item.get("id"):
                by_id[str(item["id"])] = item

    normalized: list[dict[str, Any]] = []
    for spec in CONSULTATION_SECTION_SPECS:
        sid = spec["id"]
        raw = by_id.get(sid, {})
        content = str(raw.get("content") or "").strip()
        evidence = bool(raw.get("evidence_found"))
        items: list[str] = []
        raw_items = raw.get("items")
        if isinstance(raw_items, list):
            items = [str(x).strip() for x in raw_items if str(x).strip()]

        cited: list[int] = []
        raw_cites = raw.get("citations")
        if isinstance(raw_cites, list):
            for c in raw_cites:
                try:
                    cited.append(int(c))
                except (TypeError, ValueError):
                    continue

        text_for_cites = content + "\n" + "\n".join(items)
        merged = _merge_indices(
            cited, extract_citation_indices(text_for_cites), valid_indices
        )

        # Special case: documents to carry — always surface the uploaded file when
        # we have retrieval context to show it was reviewed.
        if sid == "documents_to_carry" and uploaded_filename and valid_indices:
            first = sorted(valid_indices)[0]
            carry = f"Uploaded document: {uploaded_filename} [Source {first}]"
            extra_items = [
                i
                for i in items
                if uploaded_filename.lower() not in i.lower()
                and extract_citation_indices(i)
                and all(
                    int(x) in valid_indices for x in extract_citation_indices(i)
                )
            ]
            if evidence and merged and (content or items):
                if _looks_like_advice(text_for_cites):
                    content = carry
                    items = [carry]
                    merged = [first]
                else:
                    if uploaded_filename.lower() not in text_for_cites.lower():
                        items = [carry, *extra_items]
                    else:
                        items = items or [carry]
                    if not content:
                        content = "\n".join(f"• {i}" for i in items)
                    if first not in merged:
                        merged = [first, *merged]
                    if "[Source" not in content:
                        content = f"{content.rstrip()} [Source {first}]"
            else:
                content = (
                    f"{carry}\n"
                    "No additional schedules or annexures were identified in the "
                    f"retrieved excerpts. [Source {first}]"
                )
                items = [carry]
                merged = [first]
            evidence = True
            normalized.append(
                {
                    "id": sid,
                    "title": spec["title"],
                    "content": content,
                    "items": items,
                    "evidence_found": evidence,
                    "citations": _citation_objects(merged, sources),
                }
            )
            continue

        if (
            (not content and not items)
            or not evidence
            or not merged
            or _looks_like_advice(text_for_cites)
        ):
            normalized.append(_missing_section(spec))
            continue

        if not content and items:
            content = "\n".join(f"• {i}" for i in items)
        if "[Source" not in content and merged:
            markers = " ".join(f"[Source {i}]" for i in merged)
            content = f"{content.rstrip()} {markers}".strip()

        normalized.append(
            {
                "id": sid,
                "title": spec["title"],
                "content": content,
                "items": items,
                "evidence_found": True,
                "citations": _citation_objects(merged, sources),
            }
        )
    return normalized


def format_consultation_for_chat(sections: list[dict[str, Any]]) -> str:
    lines = ["Prepare for Consultation", ""]
    for sec in sections:
        lines.append(sec["title"])
        lines.append(sec["content"])
        if sec.get("citations"):
            chips = ", ".join(
                f"Source {c['index']}"
                + (f" p.{c['page']}" if c.get("page") is not None else "")
                for c in sec["citations"]
            )
            lines.append(f"Citations: {chips}")
        lines.append("")
    lines.append(
        "DISCLAIMER: This summary is for informational purposes only. "
        "It is not legal advice."
    )
    return "\n".join(lines).strip()


__all__ = [
    "normalize_consultation_sections",
    "format_consultation_for_chat",
    "parse_llm_json",
    "_MISSING",
]
