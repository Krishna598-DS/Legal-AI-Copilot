"""Pure grounding helpers for legal risk highlighting (no LLM / vector deps)."""

from __future__ import annotations

from typing import Any

from src.llm.risk_prompts import RISK_SPECS
from src.services.explain_grounding import (
    extract_citation_indices,
    parse_llm_json,
)

_NO_EVIDENCE = "No evidence found"
_SEVERITIES = ("High", "Medium", "Low")
_SEVERITY_RANK = {"High": 0, "Medium": 1, "Low": 2}


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


def _normalize_severity(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().title()
    if text in _SEVERITIES:
        return text
    lower = text.lower()
    for sev in _SEVERITIES:
        if sev.lower() in lower:
            return sev
    return None


def _missing_risk(spec: dict[str, str]) -> dict[str, Any]:
    return {
        "id": spec["id"],
        "title": spec["title"],
        "explanation": _NO_EVIDENCE,
        "severity": None,
        "evidence_found": False,
        "citations": [],
    }


def normalize_risks(
    parsed: dict[str, Any],
    sources: list[dict],
) -> list[dict[str, Any]]:
    """
    Ensure all checklist risks exist; drop ungrounded / uncited flags.
    """
    valid_indices = {
        int(s["index"]) for s in sources if s.get("index") is not None
    }
    by_id: dict[str, dict] = {}
    raw_risks = parsed.get("risks") if isinstance(parsed, dict) else None
    if isinstance(raw_risks, list):
        for item in raw_risks:
            if isinstance(item, dict) and item.get("id"):
                by_id[str(item["id"])] = item

    normalized: list[dict[str, Any]] = []
    for spec in RISK_SPECS:
        sid = spec["id"]
        raw = by_id.get(sid, {})
        explanation = str(raw.get("explanation") or "").strip()
        evidence = bool(raw.get("evidence_found"))
        severity = _normalize_severity(raw.get("severity"))
        title = str(raw.get("title") or spec["title"]).strip() or spec["title"]

        cited: list[int] = []
        raw_cites = raw.get("citations")
        if isinstance(raw_cites, list):
            for c in raw_cites:
                try:
                    cited.append(int(c))
                except (TypeError, ValueError):
                    continue
        from_text = extract_citation_indices(explanation)
        merged: list[int] = []
        seen: set[int] = set()
        for idx in cited + from_text:
            if idx in valid_indices and idx not in seen:
                seen.add(idx)
                merged.append(idx)

        no_evidence_text = explanation.lower() in {
            "no evidence found",
            "no evidence found.",
        }

        if (
            not evidence
            or no_evidence_text
            or not explanation
            or not merged
            or severity is None
        ):
            normalized.append(_missing_risk(spec))
            continue

        if "[Source" not in explanation and merged:
            markers = " ".join(f"[Source {i}]" for i in merged)
            explanation = f"{explanation.rstrip()} {markers}".strip()

        normalized.append(
            {
                "id": sid,
                "title": title,
                "explanation": explanation,
                "severity": severity,
                "evidence_found": True,
                "citations": _citation_objects(merged, sources),
            }
        )

    # Surface supported risks first: High → Medium → Low, then checklist order.
    order_index = {spec["id"]: i for i, spec in enumerate(RISK_SPECS)}
    normalized.sort(
        key=lambda r: (
            0 if r["evidence_found"] else 1,
            _SEVERITY_RANK.get(r["severity"] or "", 9),
            order_index.get(r["id"], 99),
        )
    )
    return normalized


def format_risks_for_chat(risks: list[dict[str, Any]]) -> str:
    lines = ["Legal Risk Highlights", ""]
    for risk in risks:
        lines.append(f"{risk['title']} [{risk['severity'] or 'N/A'}]")
        lines.append(risk["explanation"])
        if risk.get("citations"):
            chips = ", ".join(
                f"Source {c['index']}"
                + (f" p.{c['page']}" if c.get("page") is not None else "")
                for c in risk["citations"]
            )
            lines.append(f"Citations: {chips}")
        lines.append("")
    return "\n".join(lines).strip()


# Re-export for tests that prefer one import path.
__all__ = [
    "normalize_risks",
    "format_risks_for_chat",
    "parse_llm_json",
    "_NO_EVIDENCE",
]
