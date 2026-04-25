# llm_chain.py
# PURPOSE: Connect GPT to retrieval using smart prompt templates
# Day 7 Update: Now uses specialized prompts per question type

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from src.ingestion.document_loader import load_document
from src.ingestion.text_chunker import chunk_documents
from src.ingestion.embeddings import create_embeddings
from src.ingestion.vector_store import (
    load_vector_store,
    create_vector_store,
    VECTOR_STORE_PATH
)
from src.retrieval.retriever import (
    get_retriever,
    retrieve_relevant_chunks,
    format_retrieved_chunks
)
from src.llm.prompt_templates import get_prompt_template, classify_question

load_dotenv()


def create_llm():
    """
    Create and return our GPT model.
    temperature=0 for consistent, deterministic answers.
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    print("LLM loaded: gpt-4o-mini (temperature=0)")
    return llm


def answer_question(question: str, retriever, llm):
    """
    Complete RAG pipeline with smart prompt selection.

    Flow:
    1. Classify question type
    2. Retrieve relevant chunks
    3. Select appropriate prompt template
    4. Format prompt with context + question
    5. Send to GPT
    6. Return structured answer

    Args:
        question: User question in plain English
        retriever: Our FAISS retriever
        llm: Our GPT model

    Returns:
        Dictionary with answer, sources, and metadata
    """

    print(f"\n{'='*60}")
    print(f"QUESTION: {question}")
    print(f"{'='*60}")

    # Step 1: Classify the question
    question_type = classify_question(question)

    # Step 2: Retrieve relevant chunks from FAISS
    print(f"Retrieving relevant chunks...")
    chunks = retrieve_relevant_chunks(question, retriever)
    context = format_retrieved_chunks(chunks)

    # Step 3: Get the right prompt template
    prompt_template = get_prompt_template(question_type)

    # Step 4: Format the prompt with actual values
    # This replaces {context} and {question} placeholders
    formatted_prompt = prompt_template.format_messages(
        context=context,
        question=question
    )

    # Step 5: Send to GPT
    print(f"Sending to GPT with {question_type} template...")
    response = llm.invoke(formatted_prompt)

    # Step 6: Extract answer
    answer = response.content

    return {
        "question": question,
        "question_type": question_type,
        "answer": answer,
        "source_chunks": chunks,
        "num_sources": len(chunks)
    }


def print_result(result):
    """Pretty print a result."""
    print(f"\nQUESTION TYPE: {result['question_type'].upper()}")
    print(f"\nANSWER:\n{result['answer']}")
    print(f"\nSources used: {result['num_sources']} chunks")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("RAG SYSTEM - DAY 7: SMART PROMPT TEMPLATES")
    print("="*60)

    # Load all components
    embeddings_model = create_embeddings()

    try:
        vector_store = load_vector_store(embeddings_model)
    except FileNotFoundError:
        documents = load_document("data/raw/sample_contract.txt")
        chunks = chunk_documents(documents)
        vector_store = create_vector_store(chunks, embeddings_model)

    retriever = get_retriever(vector_store, k=2)
    llm = create_llm()

    # Test all three template types
    test_questions = [
        "What is the penalty for late payment?",
        "What are my obligations if I want to terminate?",
        "How long does the confidentiality obligation last?",
        "What is the CEO's name?"
    ]

    for question in test_questions:
        result = answer_question(question, retriever, llm)
        print_result(result)
