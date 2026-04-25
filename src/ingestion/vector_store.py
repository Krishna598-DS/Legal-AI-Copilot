# vector_store.py
# PURPOSE: Store and retrieve document vectors using FAISS
# This is Step 4 of our RAG pipeline: Vectors → Searchable Database

import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from src.ingestion.document_loader import load_document
from src.ingestion.text_chunker import chunk_documents
from src.ingestion.embeddings import create_embeddings

# Load API key
load_dotenv()

# Path where we save our FAISS index on disk
VECTOR_STORE_PATH = "data/processed/faiss_index"


def create_vector_store(chunks, embeddings_model):
    """
    Create a FAISS vector store from document chunks.

    What happens inside:
    1. Each chunk's text is sent to OpenAI embeddings API
    2. OpenAI returns a 1536-dimensional vector for each chunk
    3. FAISS stores all vectors in an optimized index structure
    4. The index is saved to disk for reuse

    Args:
        chunks: List of Document objects from text_chunker
        embeddings_model: Our OpenAI embeddings model

    Returns:
        FAISS vector store object
    """
    print(f"Creating vector store from {len(chunks)} chunks...")

    # This single line does a LOT:
    # - Embeds every chunk by calling OpenAI API
    # - Creates a FAISS index
    # - Stores vectors + original text + metadata together
    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings_model
    )

    # Save to disk so we don't have to rebuild every time
    vector_store.save_local(VECTOR_STORE_PATH)

    print(f"Vector store created and saved to: {VECTOR_STORE_PATH}")
    print(f"Total vectors stored: {vector_store.index.ntotal}")

    return vector_store


def load_vector_store(embeddings_model):
    """
    Load an existing FAISS index from disk.

    Why this matters:
    In production, we build the index ONCE when a document is uploaded.
    Then we load it for EVERY user question — no re-embedding needed.
    This makes responses instant instead of waiting 10-30 seconds.

    Args:
        embeddings_model: Same model used to create the store
                         (must match or search breaks)

    Returns:
        FAISS vector store object ready for search
    """
    if not os.path.exists(VECTOR_STORE_PATH):
        raise FileNotFoundError(
            f"No vector store found at {VECTOR_STORE_PATH}. "
            f"Run create_vector_store() first."
        )

    print(f"Loading vector store from disk: {VECTOR_STORE_PATH}")

    vector_store = FAISS.load_local(
        VECTOR_STORE_PATH,
        embeddings_model,
        # This flag allows loading files created on other machines
        allow_dangerous_deserialization=True
    )

    print(f"Vector store loaded successfully!")
    print(f"Total vectors in store: {vector_store.index.ntotal}")

    return vector_store


def search_vector_store(query: str, vector_store, k: int = 3):
    """
    Search the vector store for chunks similar to a query.

    What happens inside:
    1. Query text is embedded into a vector using OpenAI
    2. FAISS compares query vector against all stored vectors
    3. Returns k most similar chunks with their similarity scores

    Args:
        query: User's question in plain English
        vector_store: Our loaded FAISS index
        k: Number of results to return (3 is good default)

    Returns:
        List of (Document, score) tuples
    """
    print(f"\nSearching for: '{query}'")
    print(f"Returning top {k} most relevant chunks...")

    # similarity_search_with_score returns chunks AND their scores
    results = vector_store.similarity_search_with_score(query, k=k)

    return results


if __name__ == "__main__":
    # Step 1: Load and chunk document
    documents = load_document("data/raw/sample_contract.txt")
    chunks = chunk_documents(documents)

    # Step 2: Create embedding model
    embeddings_model = create_embeddings()

    # Step 3: Create and save vector store
    vector_store = create_vector_store(chunks, embeddings_model)

    print("\n--- TESTING SEARCH ---")

    # Test Query 1: Payment related
    results = search_vector_store(
        "What is the penalty for late payment?",
        vector_store,
        k=2
    )

    for i, (doc, score) in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"Similarity Score: {score:.4f}")
        print(f"Content: {doc.page_content[:200]}...")
        print(f"Source: {doc.metadata['source']}")

    print("\n--- TESTING LOAD FROM DISK ---")

    # Test that loading from disk works correctly
    loaded_store = load_vector_store(embeddings_model)

    results2 = search_vector_store(
        "How many days notice is required for termination?",
        loaded_store,
        k=2
    )

    for i, (doc, score) in enumerate(results2):
        print(f"\nResult {i+1}:")
        print(f"Similarity Score: {score:.4f}")
        print(f"Content: {doc.page_content[:200]}...")
