"""Request-scoped logging context (request_id, user_id)."""

from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_user_id() -> str | None:
    return user_id_var.get()


def set_request_id(value: str | None):
    return request_id_var.set(value)


def set_user_id(value: str | None):
    return user_id_var.set(value)


def reset_request_id(token) -> None:
    request_id_var.reset(token)


def reset_user_id(token) -> None:
    user_id_var.reset(token)
