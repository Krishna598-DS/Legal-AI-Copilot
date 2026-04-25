# document_loader.py
# PURPOSE: Load legal documents - supports TXT and PDF
# Updated Day 13: Added PDF support via PyMuPDF

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader

load_dotenv()


def load_document(file_path: str):
    """
    Load a document from a file path.
    Automatically detects file type and uses correct loader.

    Supported formats:
    - .txt: Plain text files
    - .pdf: PDF documents (using PyMuPDF)

    Why PyMuPDF over other PDF loaders?
    - Fastest PDF parser available in Python
    - Handles complex PDFs with tables and columns
    - Preserves page numbers in metadata
    - More reliable than pypdf or pdfminer

    Args:
        file_path: Path to the document file

    Returns:
        List of Document objects with page_content and metadata
    """
    print(f"Loading document: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document not found: {file_path}")

    # Detect file type
    extension = Path(file_path).suffix.lower()

    if extension == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")

    elif extension == ".pdf":
        # PyMuPDFLoader loads each page as a separate Document
        # This is better than loading the whole PDF as one chunk
        # because page numbers are preserved in metadata
        loader = PyMuPDFLoader(file_path)

    else:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: .txt, .pdf"
        )

    documents = loader.load()

    print(f"Successfully loaded {len(documents)} page(s)")
    print(f"File type: {extension}")
    print(f"Total characters: {sum(len(d.page_content) for d in documents)}")

    return documents


if __name__ == "__main__":
    # Test with sample contract
    docs = load_document("data/raw/sample_contract.txt")
    print("\n--- DOCUMENT PREVIEW ---")
    print(docs[0].page_content[:300])
    print("\n--- METADATA ---")
    print(docs[0].metadata)
