"""Build a printable PDF for Prepare for Consultation briefings."""

from __future__ import annotations

from typing import Any

import fitz


DISCLAIMER = (
    "DISCLAIMER: This briefing summarizes retrieved excerpts from your uploaded "
    "document for consultation preparation only. It is not legal advice and does "
    "not create an attorney-client relationship."
)


def _wrap_lines(text: str, max_chars: int = 95) -> list[str]:
    lines: list[str] = []
    for paragraph in (text or "").splitlines() or [""]:
        if not paragraph.strip():
            lines.append("")
            continue
        words = paragraph.split()
        current: list[str] = []
        for word in words:
            trial = (" ".join(current + [word])).strip()
            if len(trial) <= max_chars:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
    return lines


def build_consultation_pdf(
    *,
    filename: str,
    sections: list[dict[str, Any]],
    disclaimer: str | None = None,
) -> bytes:
    """
    Render a simple multi-page A4 PDF from structured consultation sections.
    """
    doc = fitz.open()
    page_width, page_height = fitz.paper_rect("a4").width, fitz.paper_rect("a4").height
    margin = 48
    y = margin
    page = doc.new_page(width=page_width, height=page_height)

    def ensure_space(needed: float = 28) -> None:
        nonlocal page, y
        if y + needed > page_height - margin:
            page = doc.new_page(width=page_width, height=page_height)
            y = margin

    def write(
        text: str,
        *,
        fontsize: float = 10,
        fontname: str = "helv",
        color: tuple[float, float, float] = (0.1, 0.1, 0.12),
        gap: float = 4,
    ) -> None:
        nonlocal y
        for line in _wrap_lines(text, max_chars=92 if fontsize <= 10 else 70):
            ensure_space(fontsize + 8)
            page.insert_text(
                (margin, y),
                line,
                fontsize=fontsize,
                fontname=fontname,
                color=color,
            )
            y += fontsize + gap

    write("Prepare for Consultation", fontsize=16, fontname="helv")
    y += 4
    write(f"Document: {filename}", fontsize=11)
    y += 6
    write(
        "Informational document summary only — not legal advice.",
        fontsize=9,
        color=(0.35, 0.35, 0.4),
    )
    y += 10

    for sec in sections:
        ensure_space(40)
        write(str(sec.get("title") or "Section"), fontsize=12, fontname="helv")
        body = str(sec.get("content") or "").strip()
        write(body if body else "Not found in the retrieved excerpts of this document.")
        cites = sec.get("citations") or []
        if cites:
            chips = ", ".join(
                f"Source {c.get('index')}"
                + (f" p.{c.get('page')}" if c.get("page") is not None else "")
                for c in cites
                if isinstance(c, dict)
            )
            write(f"Citations: {chips}", fontsize=9, color=(0.25, 0.4, 0.45))
        y += 8

    y += 6
    write(disclaimer or DISCLAIMER, fontsize=8, color=(0.35, 0.35, 0.4))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
