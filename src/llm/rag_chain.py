# rag_chain.py
# PURPOSE: Complete RAG chain using LCEL
# Day 8: Everything connected in one elegant pipeline

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from src.ingestion.document_loader import load_document
from src.ingestion.text_chunker import chunk_documents
from src.ingestion.embeddings import create_embeddings
from src.ingestion.vector_store import (
    load_vector_store,
    create_vector_store,
    VECTOR_STORE_PATH
)
from src.retrieval.retriever import get_retriever
from src.llm.prompt_templates import (
    get_prompt_template,
    classify_question
)

load_dotenv()


def format_docs(docs):
    """
    Format retrieved documents into a single context string.

    Why a separate function?
    LCEL chains pass data through pipe operators.
    The retriever returns a list of Documents.
    The prompt needs a single string.
    This function is the bridge between them.

    Args:
        docs: List of Document objects from retriever

    Returns:
        Single formatted string with all chunk content
    """
    formatted = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get('source', 'Unknown')
        formatted.append(f"[Source {i+1}: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


def build_rag_chain(retriever, llm, question_type: str = "general"):
    """
    Build a complete RAG chain using LCEL pipe operator.

    Chain structure:
    RunnableParallel runs TWO things simultaneously:
      1. "context": retriever fetches chunks → format_docs converts to string
      2. "question": RunnablePassthrough just passes the question through unchanged

    Then the prompt template fills {context} and {question} placeholders.
    Then the LLM generates an answer.
    Then StrOutputParser extracts just the text from the response object.

    Why RunnableParallel?
    We need BOTH context AND question available when the prompt runs.
    RunnableParallel prepares both at the same time efficiently.

    Args:
        retriever: Our FAISS retriever
        llm: Our GPT model
        question_type: Which prompt template to use

    Returns:
        Runnable LCEL chain
    """
    # Get the right prompt template
    prompt = get_prompt_template(question_type)

    # Build the chain using pipe operator
    # Each | passes output of left component to input of right component
    rag_chain = (
        RunnableParallel({
            # Retriever gets the question, returns docs, format_docs converts to string
            "context": retriever | format_docs,
            # RunnablePassthrough just passes the question through unchanged
            "question": RunnablePassthrough()
        })
        | prompt      # Fill {context} and {question} in template
        | llm         # Send filled prompt to GPT
        | StrOutputParser()  # Extract text from GPT response object
    )

    return rag_chain


def run_rag_chain(question: str, retriever, llm):
    """
    Main entry point for the RAG system.

    This is the function our API and UI will call.
    It handles question classification and chain building automatically.

    Args:
        question: User's question in plain English
        retriever: Our FAISS retriever
        llm: Our GPT model

    Returns:
        Dictionary with answer and metadata
    """
    # Classify question to pick right template
    question_type = classify_question(question)

    # Build chain with appropriate template
    chain = build_rag_chain(retriever, llm, question_type)

    # Run the chain — this single line does everything:
    # retrieve → format → prompt → llm → parse
    print(f"Running RAG chain for: '{question}'")
    answer = chain.invoke(question)

    return {
        "question": question,
        "question_type": question_type,
        "answer": answer
    }


def run_rag_chain_with_sources(question: str, retriever, llm):
    """
    Same as run_rag_chain but also returns source documents.

    Why a separate function?
    The basic chain returns only the answer string.
    For our UI we want to show users which chunks were used.
    This version runs retrieval separately to capture sources.

    In production this is what the UI calls — users want
    to verify where the answer came from.

    Args:
        question: User's question
        retriever: Our FAISS retriever
        llm: Our GPT model

    Returns:
        Dictionary with answer, sources, and metadata
    """
    # Classify question
    question_type = classify_question(question)

    # Get source documents separately
    source_docs = retriever.invoke(question)

    # Build and run chain
    chain = build_rag_chain(retriever, llm, question_type)
    answer = chain.invoke(question)

    # Format sources for display
    sources = []
    for doc in source_docs:
        sources.append({
            "content": doc.page_content[:200] + "...",
            "source": doc.metadata.get("source", "Unknown"),
            "full_content": doc.page_content
        })

    return {
        "question": question,
        "question_type": question_type,
        "answer": answer,
        "sources": sources,
        "num_sources": len(sources)
    }


if __name__ == "__main__":
    print("="*60)
    print("RAG SYSTEM - DAY 8: FULL LCEL CHAIN")
    print("="*60)

    # Initialize all components
    embeddings_model = create_embeddings()

    try:
        vector_store = load_vector_store(embeddings_model)
    except FileNotFoundError:
        documents = load_document("data/raw/sample_contract.txt")
        chunks = chunk_documents(documents)
        vector_store = create_vector_store(chunks, embeddings_model)

    retriever = get_retriever(vector_store, k=2)

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    print("\n--- TEST 1: BASIC CHAIN ---")
    test_questions = [
        "What is the penalty for late payment?",
        "What are my obligations when terminating?",
        "Who are the parties in this agreement?"
    ]

    for question in test_questions:
        result = run_rag_chain(question, retriever, llm)
        print(f"\nQ: {result['question']}")
        print(f"Type: {result['question_type']}")
        print(f"A: {result['answer']}")
        print("-"*60)

    print("\n--- TEST 2: CHAIN WITH SOURCES ---")
    result = run_rag_chain_with_sources(
        "What happens if payment is late?",
        retriever,
        llm
    )

    print(f"\nQ: {result['question']}")
    print(f"Type: {result['question_type']}")
    print(f"\nANSWER:\n{result['answer']}")
    print(f"\nSOURCES USED: {result['num_sources']}")
    for i, source in enumerate(result['sources']):
        print(f"\nSource {i+1}: {source['source']}")
        print(f"Preview: {source['content']}")
