"""Text chunking for embedding and retrieval."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import get_settings
from src.logging_config import logger


def chunk_documents(documents, chunk_size: int | None = None, chunk_overlap: int | None = None):
    """Split documents into overlapping chunks (defaults from settings)."""
    settings = get_settings()
    size = settings.CHUNK_SIZE if chunk_size is None else chunk_size
    overlap = settings.CHUNK_OVERLAP if chunk_overlap is None else chunk_overlap
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info(
        "Chunked %s document(s) → %s chunks (size=%s, overlap=%s)",
        len(documents),
        len(chunks),
        size,
        overlap,
    )
    return chunks
