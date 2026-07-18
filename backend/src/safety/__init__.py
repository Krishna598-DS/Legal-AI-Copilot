"""Legal AI Safety Layer — information vs advice, prompt + output guardrails."""

from src.safety.confidence_messaging import build_low_confidence_message
from src.safety.guardrails import (
    find_safety_violations,
    is_unsafe_legal_output,
    sanitize_legal_output,
    scrub_structured_items,
)
from src.safety.policy import (
    FORBIDDEN_BEHAVIORS,
    LEGAL_ADVICE,
    LEGAL_INFORMATION,
    SAFETY_DISCLAIMER,
)
from src.safety.prompts import SAFETY_SYSTEM_BLOCK, with_safety_preamble

__all__ = [
    "LEGAL_INFORMATION",
    "LEGAL_ADVICE",
    "FORBIDDEN_BEHAVIORS",
    "SAFETY_DISCLAIMER",
    "SAFETY_SYSTEM_BLOCK",
    "with_safety_preamble",
    "find_safety_violations",
    "is_unsafe_legal_output",
    "sanitize_legal_output",
    "scrub_structured_items",
    "build_low_confidence_message",
]
