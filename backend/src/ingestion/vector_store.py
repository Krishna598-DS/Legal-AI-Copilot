"""FAISS vector store create / load / delete."""

import os
import shutil

from langchain_community.vectorstores import FAISS

from src.logging_config import logger
from src.observability.events import log_event

# Legacy default path (demos). Product code always passes persist_path.
VECTOR_STORE_PATH = "data/processed/faiss_index"


def create_vector_store(chunks, embeddings_model, persist_path: str | None = None):
    path = persist_path or VECTOR_STORE_PATH
    os.makedirs(path, exist_ok=True)
    log_event(
        logger,
        "embedding",
        message="embedding documents",
        chunk_count=len(chunks),
        persist_path=path,
    )
    vector_store = FAISS.from_documents(documents=chunks, embedding=embeddings_model)
    vector_store.save_local(path)
    log_event(
        logger,
        "embedding",
        message="FAISS index saved",
        persist_path=path,
        vector_count=vector_store.index.ntotal,
    )
    return vector_store


def load_vector_store(embeddings_model, persist_path: str | None = None):
    path = persist_path or VECTOR_STORE_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"No vector store found at {path}")
    vector_store = FAISS.load_local(
        path,
        embeddings_model,
        allow_dangerous_deserialization=True,
    )
    logger.info("FAISS index loaded from %s (%s vectors)", path, vector_store.index.ntotal)
    return vector_store


def delete_vector_store(persist_path: str) -> None:
    if persist_path and os.path.isdir(persist_path):
        shutil.rmtree(persist_path, ignore_errors=True)


def search_vector_store(query: str, vector_store, k: int = 3):
    return vector_store.similarity_search_with_score(query, k=k)
