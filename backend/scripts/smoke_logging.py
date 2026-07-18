"""Smoke-test JSON formatter + log_event without full app deps."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from src.observability.context import reset_request_id, set_request_id
from src.observability.events import log_event
from src.observability.formatter import JsonFormatter


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []
        self.setFormatter(JsonFormatter())

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


def main() -> None:
    record = logging.LogRecord(
        "legal_rag", logging.INFO, __file__, 1, "hello", (), None
    )
    record.event = "login"
    record.request_id = "abc"
    record.user_id = "u1"
    record.status_code = 200
    record.latency_ms = 12.5
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "login"
    assert payload["request_id"] == "abc"
    assert payload["user_id"] == "u1"
    assert payload["status_code"] == 200
    assert payload["latency_ms"] == 12.5

    log = logging.getLogger("legal_rag_smoke")
    log.handlers.clear()
    handler = _ListHandler()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False

    token = set_request_id("req-9")
    try:
        log_event(
            log, "retrieval", message="chunks", chunk_count=3, user_id="u2"
        )
    finally:
        reset_request_id(token)

    event_payload = json.loads(handler.lines[-1])
    assert event_payload["event"] == "retrieval"
    assert event_payload["request_id"] == "req-9"
    assert event_payload["chunk_count"] == 3
    print("SMOKE_OK", json.dumps(event_payload))


if __name__ == "__main__":
    main()
