"""Centralized application settings (Pydantic Settings).

Supports ENVIRONMENT=development|testing|production.
Loads `.env` then `.env.{environment}` when present.

Attribute names used across the app remain backward compatible
(e.g. settings.OPENAI_API_KEY, settings.SECRET_KEY, settings.LLM_MODEL).
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["development", "testing", "production"]

WEAK_SECRETS = {
    "",
    "change-me-in-production-use-a-long-random-string",
    "secret",
    "changeme",
}

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _discover_env_files() -> tuple[str, ...]:
    """Return existing env files: `.env` then `.env.{ENVIRONMENT}`."""
    env_name = os.getenv("ENVIRONMENT", "development").strip().lower() or "development"
    aliases = {"dev": "development", "test": "testing", "prod": "production"}
    env_name = aliases.get(env_name, env_name)
    candidates = [
        _REPO_ROOT / ".env",
        Path.cwd() / ".env",
        _REPO_ROOT / f".env.{env_name}",
        Path.cwd() / f".env.{env_name}",
    ]
    seen: set[str] = set()
    files: list[str] = []
    for path in candidates:
        if not path.is_file():
            continue
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            files.append(str(path))
    return tuple(files)


class Settings(BaseSettings):
    """Application configuration — environment variables override file defaults."""

    model_config = SettingsConfigDict(
        env_file=_discover_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # ── App / environment ───────────────────────────────────────
    APP_NAME: str = "AI Legal Copilot"
    APP_VERSION: str = "3.1.0"
    ENVIRONMENT: EnvironmentName = "development"
    APP_BASE_URL: str = "http://localhost:8010"
    FRONTEND_URL: str = "http://localhost:8010"
    FRONTEND_DIR: str = ""
    ADMIN_EMAILS: str = ""
    # Professional discovery: "local" (manual DB). Future: external directory adapters.
    DIRECTORY_PROVIDER: str = Field(
        default="local",
        description="Professional directory backend: local | (future adapters)",
    )

    # ── Secrets / auth (JWT) ────────────────────────────────────
    OPENAI_API_KEY: str = ""
    SECRET_KEY: str = Field(
        default="change-me-in-production-use-a-long-random-string",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"),
        description="JWT signing secret",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,
        validation_alias=AliasChoices(
            "ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_EXPIRE_MINUTES"
        ),
        description="JWT access-token lifetime in minutes",
    )
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_HOURS: int = 24

    # ── Database / in-memory cache ──────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/app.db"
    REDIS_URL: str = ""
    CACHE_SIZE: int = Field(
        default=0,
        description="Max in-memory RAG instances (0 = unlimited)",
    )

    # ── CORS ────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # ── Storage paths ───────────────────────────────────────────
    DATA_DIR: str = "data"
    UPLOAD_DIR: str = ""
    INDEX_DIR: str = ""
    LOG_DIR: str = "logs"

    # ── Uploads ─────────────────────────────────────────────────
    ALLOWED_EXTENSIONS: set[str] = Field(default_factory=lambda: {".pdf", ".txt"})
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    CLAMAV_HOST: str = ""
    CLAMAV_PORT: int = 3310
    CLAMAV_TIMEOUT: float = 10.0
    ENABLE_UPLOAD_SCAN: bool = True

    # ── Rate limits ─────────────────────────────────────────────
    MAX_QUESTIONS_PER_HOUR: int = 60
    MAX_UPLOADS_PER_HOUR: int = 10
    MAX_DOCUMENTS_PER_USER: int = 20

    # ── Models / RAG ────────────────────────────────────────────
    LLM_MODEL: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("LLM_MODEL", "CHAT_MODEL"),
        description="Chat / completion model",
    )
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_TEMPERATURE: float = 0.0
    RETRIEVAL_K: int = 3
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    CHAT_MEMORY_WINDOW: int = 6
    USE_LLM_CLASSIFIER: bool = True
    HYBRID_DENSE_WEIGHT: float = 0.6
    HYBRID_BM25_WEIGHT: float = 0.4

    # ── Client resilience ───────────────────────────────────────
    REQUEST_TIMEOUT: float = Field(
        default=60.0,
        description="Timeout (seconds) for OpenAI / LLM HTTP calls",
    )
    RETRY_COUNT: int = Field(
        default=2,
        description="Retry count for OpenAI client calls",
    )

    # ── Logging ─────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: json | text",
    )
    LOG_TO_CONSOLE: bool = True
    LOG_TO_FILE: bool = True
    LOG_FILE_NAME: str = "app.log"
    LOG_MAX_BYTES: int = 5_000_000
    LOG_BACKUP_COUNT: int = 5

    # ── Email ───────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@legalrag.local"
    SMTP_TLS: bool = True
    SMTP_TIMEOUT: float = 30.0
    REQUIRE_EMAIL_VERIFICATION: bool = False

    # ── Legal versions ──────────────────────────────────────────
    TERMS_VERSION: str = "2026-07-17"
    PRIVACY_VERSION: str = "2026-07-17"

    # ── Observability / optional integrations ───────────────────
    SENTRY_DSN: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID: str = ""

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> str:
        if value is None or value == "":
            return "development"
        text = str(value).strip().lower()
        aliases = {"dev": "development", "test": "testing", "prod": "production"}
        text = aliases.get(text, text)
        if text not in {"development", "testing", "production"}:
            raise ValueError(
                "ENVIRONMENT must be one of: development, testing, production"
            )
        return text

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return value  # type: ignore[return-value]

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_extensions(cls, value: object) -> set[str]:
        if value is None or value == "":
            return {".pdf", ".txt"}
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return {p if p.startswith(".") else f".{p}" for p in parts}
        if isinstance(value, (list, tuple, set)):
            out = set()
            for item in value:
                text = str(item).strip()
                out.add(text if text.startswith(".") else f".{text}")
            return out
        return value  # type: ignore[return-value]

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> str:
        text = str(value or "INFO").strip().upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        return text if text in allowed else "INFO"

    @field_validator("LOG_FORMAT", mode="before")
    @classmethod
    def normalize_log_format(cls, value: object) -> str:
        text = str(value or "json").strip().lower()
        return text if text in {"json", "text"} else "json"

    @model_validator(mode="after")
    def resolve_paths_and_env_defaults(self) -> Settings:
        if not self.UPLOAD_DIR:
            self.UPLOAD_DIR = str(Path(self.DATA_DIR) / "uploads")
        if not self.INDEX_DIR:
            self.INDEX_DIR = str(Path(self.DATA_DIR) / "indexes")
        if not self.FRONTEND_DIR:
            self.FRONTEND_DIR = str(_REPO_ROOT / "frontend")

        # Testing defaults when env vars are not explicitly set
        if self.ENVIRONMENT == "testing":
            if os.getenv("LOG_LEVEL") is None and self.LOG_LEVEL == "INFO":
                self.LOG_LEVEL = "WARNING"
            if os.getenv("REQUIRE_EMAIL_VERIFICATION") is None:
                self.REQUIRE_EMAIL_VERIFICATION = False
        return self

    # Read-only convenience aliases
    @property
    def jwt_secret(self) -> str:
        return self.SECRET_KEY

    @property
    def jwt_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def chat_model(self) -> str:
        return self.LLM_MODEL

    @property
    def upload_directory(self) -> str:
        return self.UPLOAD_DIR

    @property
    def index_directory(self) -> str:
        return self.INDEX_DIR


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Call clear_settings_cache() in tests."""
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def validate_settings(settings: Settings | None = None) -> list[str]:
    """Return warnings; raise in production on critical misconfig."""
    settings = settings or get_settings()
    warnings: list[str] = []

    if settings.SECRET_KEY in WEAK_SECRETS or len(settings.SECRET_KEY) < 32:
        msg = "SECRET_KEY is weak or default — set a long random value"
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(msg)
        warnings.append(msg)

    if not settings.OPENAI_API_KEY:
        warnings.append("OPENAI_API_KEY is not set")

    if settings.ENVIRONMENT == "production" and settings.DATABASE_URL.startswith(
        "sqlite"
    ):
        warnings.append("Using SQLite in production — prefer Postgres")

    if warnings:
        # Lazy import avoids circular dependency at module import time
        try:
            from src.logging_config import logger

            for warning in warnings:
                logger.warning(warning, extra={"event": "config_warning"})
        except Exception:
            for warning in warnings:
                sys.stderr.write(f"CONFIG WARNING: {warning}\n")
    return warnings
