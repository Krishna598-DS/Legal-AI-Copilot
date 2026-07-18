"""Shared formatting helpers for RAG context."""


def format_docs(docs) -> str:
    """Turn retrieved Document objects into a single context string."""
    parts = []
    for i, doc in enumerate(docs, start=1):
        page = doc.metadata.get("page_number") or doc.metadata.get("page")
        source = doc.metadata.get("source", "document")
        page_bit = f" | page {page}" if page is not None else ""
        parts.append(f"[Source {i}{page_bit} | {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)
