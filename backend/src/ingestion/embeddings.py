"""OpenAI embeddings factory."""

from langchain_openai import OpenAIEmbeddings

from src.config import get_settings
from src.errors import OpenAIServiceError
from src.logging_config import logger
from src.observability.events import log_event


def create_embeddings():
    """Return the shared OpenAI embeddings client."""
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        raise OpenAIServiceError(
            "AI service is not configured.",
            code="OPENAI_NOT_CONFIGURED",
        )
    kwargs = {
        "model": settings.EMBEDDING_MODEL,
        "openai_api_key": settings.OPENAI_API_KEY,
        "max_retries": settings.RETRY_COUNT,
    }
    try:
        embeddings = OpenAIEmbeddings(
            **kwargs, request_timeout=settings.REQUEST_TIMEOUT
        )
    except TypeError:
        embeddings = OpenAIEmbeddings(**kwargs, timeout=settings.REQUEST_TIMEOUT)
    log_event(
        logger,
        "embedding",
        message="embeddings client ready",
        model=settings.EMBEDDING_MODEL,
    )
    return embeddings


def embed_text(text: str, embeddings_model) -> list:
    """Embed a single string."""
    return embeddings_model.embed_query(text)
