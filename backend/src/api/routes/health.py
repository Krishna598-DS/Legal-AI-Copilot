"""Liveness, readiness, and detailed health endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from src.config import get_settings
from src.services import health_service

router = APIRouter(tags=["health"])
settings = get_settings()


class HealthChecks(BaseModel):
    database: str
    storage: str
    openai: str
    faiss: str


class HealthResponse(BaseModel):
    status: str
    checks: HealthChecks
    version: str | None = None
    details: dict[str, str] = Field(default_factory=dict)


class LiveResponse(BaseModel):
    status: str = "alive"
    version: str


def _as_response_model(payload: dict[str, Any]) -> HealthResponse:
    return HealthResponse(
        status=payload["status"],
        checks=HealthChecks(**payload["checks"]),
        version=payload.get("version"),
        details=payload.get("details") or {},
    )


@router.get("/live", response_model=LiveResponse)
def liveness() -> LiveResponse:
    """Kubernetes-style liveness: process is up."""
    return LiveResponse(status="alive", version=settings.APP_VERSION)


@router.get("/ready", response_model=HealthResponse)
def readiness(response: Response) -> HealthResponse:
    """
    Readiness probe: database, storage, OpenAI key, and FAISS must be ok.
    Returns HTTP 503 when not ready.
    """
    payload = health_service.run_checks()
    body = _as_response_model(payload)
    if not health_service.is_ready(payload):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        body.status = "unhealthy"
    return body


@router.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    """
    Detailed health check with structured dependency status.
    Returns HTTP 503 when any check fails.
    """
    payload = health_service.run_checks()
    body = _as_response_model(payload)
    if not health_service.is_ready(payload):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return body
