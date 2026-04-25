# retriever.py
# PURPOSE: Retrieve relevant document chunks for any user question
# This is Step 5 of our RAG pipeline: Question → Relevant Chunks

import os
from dotenv import load_dotenv
from src.ingestion.document_loader import load_document
from src.ingestion.text_chunker import chunk_documents
from src.ingestion.embeddings import create_embeddings
from src.ingestion.vector_store import (
    create_vector_store,
    load_vector_store,
    VECTOR_STORE_PATH
)

load_dotenv()


def get_retriever(vector_store, k: int = 3):
    """
    Convert a FAISS vector store into a LangChain retriever.

    Why use a retriever instead of searching directly?
    - Standard LangChain interface — works with any vector store
    - Plugs directly into RAG chains (Week 2) without changes
    - Abstracts the search details from the rest of the system

    Args:
        vector_store: Our loaded FAISS vector store
        k: Number of chunks to retrieve per question

    Returns:
        LangChain retriever object
    """
    retriever = vector_store.as_retriever(
        search_type="similarity",      # Simple cosine/L2 similarity
        search_kwargs={"k": k}         # Return top k results
    )

    print(f"Retriever created (k={k}, search_type=similarity)")
    return retriever


def retrieve_relevant_chunks(question: str, retriever):
    """
    Find the most relevant document chunks for a question.

    Args:
        question: User's question in plain English
        retriever: Our LangChain retriever

    Returns:
        List of relevant Document objects
    """
    print(f"\nQuestion: '{question}'")

    # invoke() sends the question through the retriever
    # Internally: embeds question → searches FAISS → returns chunks
    relevant_chunks = retriever.invoke(question)

    print(f"Found {len(relevant_chunks)} relevant chunks")
    return relevant_chunks


def format_retrieved_chunks(chunks):
    """
    Format chunks into a clean, readable context string.
    This is what we'll eventually send to GPT as context.

    Why format them?
    - GPT needs a single string, not a list of objects
    - We add source information for transparency
    - Clean formatting helps GPT give better answers

    Args:
        chunks: List of Document objects from retriever

    Returns:
        Formatted string with all chunk content and sources
    """
    formatted = []

    for i, chunk in enumerate(chunks):
        source = chunk.metadata.get('source', 'Unknown')
        content = chunk.page_content.strip()

        formatted.append(
            f"[Source {i+1}: {source}]\n{content}"
        )

    # Join all chunks with a clear separator
    return "\n\n---\n\n".join(formatted)


def run_retrieval_pipeline(question: str, vector_store):
    """
    Complete retrieval pipeline from question to formatted context.
    This is the function our RAG chain will call in Week 2.

    Args:
        question: User's question
        vector_store: Our FAISS vector store

    Returns:
        Formatted context string ready for LLM
    """
    # Create retriever
    retriever = get_retriever(vector_store, k=2)

    # Get relevant chunks
    chunks = retrieve_relevant_chunks(question, retriever)

    # Format for LLM consumption
    context = format_retrieved_chunks(chunks)

    return context, chunks


if __name__ == "__main__":
    print("="*50)
    print("RAG RETRIEVAL PIPELINE - DAY 5 TEST")
    print("="*50)

    # Load embedding model
    embeddings_model = create_embeddings()

    # Try loading existing vector store, create if not found
    try:
        vector_store = load_vector_store(embeddings_model)
        print("Loaded existing vector store from disk")
    except FileNotFoundError:
        print("No existing vector store found, creating new one...")
        documents = load_document("data/raw/sample_contract.txt")
        chunks = chunk_documents(documents)
        vector_store = create_vector_store(chunks, embeddings_model)

    print("\n" + "="*50)
    print("TESTING 3 DIFFERENT QUESTIONS")
    print("="*50)

    # Test questions covering different parts of the contract
    test_questions = [
        "What is the penalty for late payment?",
        "How many days notice is required to terminate?",
        "How long does the confidentiality obligation last?"
    ]

    for question in test_questions:
        print(f"\n{'='*50}")
        context, chunks = run_retrieval_pipeline(
            question, vector_store
        )

        print("\n--- RETRIEVED CONTEXT ---")
        print(context)
        print(f"\n--- CHUNK COUNT: {len(chunks)} ---")
