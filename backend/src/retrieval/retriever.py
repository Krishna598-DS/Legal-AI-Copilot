"""Hybrid retriever: FAISS + BM25 when possible."""

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from src.config import get_settings
from src.logging_config import logger


def get_retriever(vector_store, k: int | None = None):
    settings = get_settings()
    top_k = settings.RETRIEVAL_K if k is None else k
    dense = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k},
    )
    try:
        docs = _all_documents(vector_store)
        if len(docs) < 2:
            return dense
        bm25 = BM25Retriever.from_documents(docs)
        bm25.k = top_k
        from langchain.retrievers import EnsembleRetriever

        logger.info("Using hybrid FAISS+BM25 retriever (k=%s)", top_k)
        return EnsembleRetriever(
            retrievers=[dense, bm25],
            weights=[settings.HYBRID_DENSE_WEIGHT, settings.HYBRID_BM25_WEIGHT],
        )
    except Exception as exc:
        logger.warning("Hybrid retriever unavailable (%s); using dense only", exc)
        return dense


def _all_documents(vector_store) -> list[Document]:
    store = getattr(vector_store, "docstore", None)
    if store is None:
        return []
    raw = getattr(store, "_dict", None) or {}
    return list(raw.values())


def format_retrieved_chunks(chunks) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        page = chunk.metadata.get("page_number") or chunk.metadata.get("page", "?")
        source = chunk.metadata.get("source", "unknown")
        parts.append(f"[Source {i} | page {page} | {source}]\n{chunk.page_content}")
    return "\n\n".join(parts)
