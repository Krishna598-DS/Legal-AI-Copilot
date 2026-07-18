"""Unit tests for centralized Pydantic settings."""

import os

import pytest

from src.config import Settings, clear_settings_cache, get_settings


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_default_environment_is_valid():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        SECRET_KEY="unit-test-secret-key-at-least-32-chars",
    )
    assert settings.ENVIRONMENT == "development"
    assert settings.UPLOAD_DIR.endswith("uploads")
    assert settings.INDEX_DIR.endswith("indexes")
    assert settings.CACHE_SIZE == 0
    assert settings.REQUEST_TIMEOUT == 60.0
    assert settings.RETRY_COUNT == 2
    assert settings.chat_model == "gpt-4o-mini"


def test_environment_aliases():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="prod",
        SECRET_KEY="unit-test-secret-key-at-least-32-chars",
    )
    assert settings.ENVIRONMENT == "production"


def test_jwt_and_chat_aliases(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "alias-secret-key-at-least-32-chars-xx")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("CHAT_MODEL", "gpt-4o-mini")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    clear_settings_cache()
    settings = Settings(_env_file=None)
    assert settings.SECRET_KEY.startswith("alias-secret")
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.LLM_MODEL == "gpt-4o-mini"


def test_cors_csv_parsing():
    settings = Settings(
        _env_file=None,
        SECRET_KEY="unit-test-secret-key-at-least-32-chars",
        CORS_ORIGINS="http://a.com, http://b.com",
    )
    assert settings.CORS_ORIGINS == ["http://a.com", "http://b.com"]


def test_get_settings_cached(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-at-least-32-chars")
    clear_settings_cache()
    a = get_settings()
    b = get_settings()
    assert a is b


def test_log_settings_from_env():
    settings = Settings(
        _env_file=None,
        SECRET_KEY="unit-test-secret-key-at-least-32-chars",
        LOG_FORMAT="TEXT",
        LOG_LEVEL="debug",
        LOG_TO_CONSOLE=False,
        LOG_TO_FILE=True,
        LOG_FILE_NAME="custom.log",
    )
    assert settings.LOG_FORMAT == "text"
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.LOG_TO_CONSOLE is False
    assert settings.LOG_TO_FILE is True
    assert settings.LOG_FILE_NAME == "custom.log"
