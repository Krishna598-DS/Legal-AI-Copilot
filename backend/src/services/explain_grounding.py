"""Pure grounding helpers for Explain My Document (no LLM / vector deps)."""

from __future__ import annotations

import json
import re
from typing import Any

from src.llm.explain_prompts import EXPLAIN_SECTION_SPECS

_MISSING = "Not found in the retrieved excerpts of this document."
_SOURCE_RE = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)


def parse_llm_json(raw: str) -> dict[str, Any]:
    """Extract a JSON object from an LLM response (tolerates markdown fences)."""
    text = (raw or "").strip()
    if not text:
        return {}
    if text.startswith("```"):
        lines = text.splitlines()
        # drop opening ```json / ``` and closing ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


def extract_citation_indices(text: str) -> list[int]:
    """Pull unique Source N indices from prose, in order of first appearance."""
    seen: set[int] = set()
    out: list[int] = []
    for match in _SOURCE_RE.finditer(text or ""):
        idx = int(match.group(1))
        if idx not in seen:
            seen.add(idx)
            out.append(idx)
    return out


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


def normalize_sections(
    parsed: dict[str, Any],
    sources: list[dict],
) -> list[dict[str, Any]]:
    """
    Ensure all required sections exist and every claim with evidence has citations.

    Claims marked evidence_found without valid citations are downgraded to missing.
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
    for spec in EXPLAIN_SECTION_SPECS:
        sid = spec["id"]
        raw = by_id.get(sid, {})
        content = str(raw.get("content") or "").strip()
        evidence = bool(raw.get("evidence_found"))
        cited = []
        raw_cites = raw.get("citations")
        if isinstance(raw_cites, list):
            for c in raw_cites:
                try:
                    cited.append(int(c))
                except (TypeError, ValueError):
                    continue
        # Prefer explicit citations; also harvest from prose.
        from_text = extract_citation_indices(content)
        merged: list[int] = []
        seen: set[int] = set()
        for idx in cited + from_text:
            if idx in valid_indices and idx not in seen:
                seen.add(idx)
                merged.append(idx)

        if not content:
            evidence = False
            content = _MISSING
            merged = []
        elif evidence and not merged:
            # Hallucinated / ungrounded claim — refuse it.
            evidence = False
            content = _MISSING
            merged = []
        elif not evidence:
            content = _MISSING
            merged = []
        else:
            # Ensure at least one inline citation marker for UI clarity.
            if "[Source" not in content and merged:
                markers = " ".join(f"[Source {i}]" for i in merged)
                content = f"{content.rstrip()} {markers}".strip()

        normalized.append(
            {
                "id": sid,
                "title": spec["title"],
                "content": content,
                "evidence_found": evidence,
                "citations": _citation_objects(merged, sources),
            }
        )
    return normalized


def format_explanation_for_chat(sections: list[dict[str, Any]]) -> str:
    """Flatten structured explanation into a chat-friendly transcript."""
    lines = ["Explain My Document", ""]
    for sec in sections:
        lines.append(f"{sec['title']}")
        lines.append(sec["content"])
        if sec.get("citations"):
            chips = ", ".join(
                f"Source {c['index']}"
                + (f" p.{c['page']}" if c.get("page") is not None else "")
                for c in sec["citations"]
            )
            lines.append(f"Citations: {chips}")
        lines.append("")
    return "\n".join(lines).strip()
