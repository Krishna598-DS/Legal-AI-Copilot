"""Document loading (TXT/PDF) with page metadata and table extraction."""

import os
from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_core.documents import Document

from src.logging_config import logger


def _extract_pdf_tables(file_path: str) -> tuple[list[Document], bool]:
    table_docs: list[Document] = []
    has_tables = False
    try:
        import fitz

        doc = fitz.open(file_path)
        for page_index, page in enumerate(doc):
            page_num = page_index + 1
            try:
                finder = page.find_tables()
            except Exception:
                continue
            for t_i, table in enumerate(getattr(finder, "tables", []) or []):
                try:
                    data = table.extract()
                except Exception:
                    continue
                if not data:
                    continue
                has_tables = True
                lines = [
                    " | ".join(str(c).strip() if c is not None else "" for c in row)
                    for row in data
                ]
                table_docs.append(
                    Document(
                        page_content=(
                            f"[Table {t_i + 1} on page {page_num}]\n" + "\n".join(lines)
                        ),
                        metadata={
                            "source": file_path,
                            "page": page_num,
                            "page_number": page_num,
                            "content_type": "table",
                        },
                    )
                )
        doc.close()
    except Exception as exc:
        logger.debug("Table extraction skipped: %s", exc)
    return table_docs, has_tables


def load_document(file_path: str) -> list[Document]:
    """Load TXT/PDF. PDF pages use 1-based page numbers; tables are appended."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document not found: {file_path}")

    extension = Path(file_path).suffix.lower()
    has_tables = False

    if extension == ".txt":
        documents = TextLoader(file_path, encoding="utf-8").load()
        for d in documents:
            d.metadata["page"] = 1
            d.metadata["page_number"] = 1
            d.metadata["content_type"] = "text"
        page_count = 1
    elif extension == ".pdf":
        documents = PyMuPDFLoader(file_path).load()
        for d in documents:
            page_num = int(d.metadata.get("page", 0)) + 1
            d.metadata["page"] = page_num
            d.metadata["page_number"] = page_num
            d.metadata["content_type"] = "text"
        page_count = len(documents)
        table_docs, has_tables = _extract_pdf_tables(file_path)
        documents.extend(table_docs)
    else:
        raise ValueError(f"Unsupported file type: {extension}. Use .txt or .pdf")

    if documents:
        documents[0].metadata["has_tables"] = has_tables
        documents[0].metadata["page_count"] = page_count

    logger.info(
        "Loaded %s (%s segments, %s chars)",
        file_path,
        len(documents),
        sum(len(d.page_content) for d in documents),
    )
    return documents
