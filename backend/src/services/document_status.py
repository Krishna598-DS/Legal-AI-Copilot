"""Document processing lifecycle statuses."""

from __future__ import annotations

# Canonical statuses (uppercase)
UPLOADING = "UPLOADING"
PROCESSING = "PROCESSING"
READY = "READY"
FAILED = "FAILED"

ALL_STATUSES = frozenset({UPLOADING, PROCESSING, READY, FAILED})

# Legacy lowercase value from earlier versions
_LEGACY_READY = "ready"


def normalize_status(status: str | None) -> str:
    if not status:
        return UPLOADING
    text = str(status).strip()
    if text == _LEGACY_READY:
        return READY
    upper = text.upper()
    return upper if upper in ALL_STATUSES else text


def is_ready(status: str | None) -> bool:
    return normalize_status(status) == READY


def is_terminal(status: str | None) -> bool:
    return normalize_status(status) in {READY, FAILED}
