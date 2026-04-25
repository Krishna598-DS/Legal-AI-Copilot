# text_chunker.py
# PURPOSE: Split large legal documents into small, searchable chunks
# This is Step 2 of our RAG pipeline: Raw Text → Chunks

from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.ingestion.document_loader import load_document


def chunk_documents(documents, chunk_size=500, chunk_overlap=50):
    """
    Split documents into chunks for embedding and retrieval.

    Args:
        documents: List of LangChain Document objects (from document_loader)
        chunk_size: Maximum characters per chunk (500 is good for legal docs)
        chunk_overlap: Characters repeated between chunks (prevents boundary cuts)

    Returns:
        List of smaller Document objects, each is one chunk
    """

    print(f"Chunking {len(documents)} document(s)...")
    print(f"Settings: chunk_size={chunk_size}, overlap={chunk_overlap}")

    # RecursiveCharacterTextSplitter tries to split in this order:
    # 1. Double newline (paragraph breaks) -- most natural
    # 2. Single newline (line breaks)
    # 3. Space (word boundaries)
    # 4. Individual characters (last resort)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,  # measure size by character count
        separators=["\n\n", "\n", " ", ""]  # order of preference for splitting
    )

    # Split all documents into chunks
    # Each chunk is still a Document object with page_content + metadata
    chunks = splitter.split_documents(documents)

    print(f"Created {len(chunks)} chunks from {len(documents)} document(s)")

    return chunks


def inspect_chunks(chunks):
    """
    Print details about each chunk so we can verify quality.
    This is a debugging/learning tool.
    """
    print(f"\n{'='*50}")
    print(f"CHUNK INSPECTION REPORT")
    print(f"Total chunks: {len(chunks)}")
    print(f"{'='*50}")

    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Size: {len(chunk.page_content)} characters")
        print(f"Content: {chunk.page_content[:200]}...")
        print(f"Metadata: {chunk.metadata}")


if __name__ == "__main__":
    # Step 1: Load the document (reusing our Day 1 work)
    documents = load_document("data/raw/sample_contract.txt")

    # Step 2: Chunk it
    chunks = chunk_documents(documents)

    # Step 3: Inspect what we created
    inspect_chunks(chunks)
