"""RAGAS evaluation harness for offline quality checks."""

import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from src.ingestion.document_loader import load_document
from src.ingestion.text_chunker import chunk_documents
from src.ingestion.embeddings import create_embeddings
from src.ingestion.vector_store import load_vector_store, create_vector_store
from src.retrieval.retriever import get_retriever, format_retrieved_chunks
from src.llm.rag_chain import build_rag_chain
from src.llm.formatting import format_docs

load_dotenv()


# ─────────────────────────────────────────────────
# TEST DATASET
# Ground truth question-answer pairs for evaluation
# In production these would be created by legal experts
# ─────────────────────────────────────────────────

TEST_DATASET = [
    {
        "question": "What is the monthly payment amount?",
        "ground_truth": "The monthly payment amount is $10,000, due on the first of each month."
    },
    {
        "question": "What is the penalty for late payment?",
        "ground_truth": "Late payments incur a 2% monthly penalty."
    },
    {
        "question": "How many days notice is required to terminate the agreement?",
        "ground_truth": "Either party may terminate the agreement with 30 days written notice."
    },
    {
        "question": "How long does the confidentiality obligation last?",
        "ground_truth": "The confidentiality obligation lasts for 5 years after termination of the agreement."
    },
    {
        "question": "What services does the Provider deliver?",
        "ground_truth": "The Provider delivers software consulting services including system design, implementation, and maintenance."
    },
    {
        "question": "Who are the parties in this agreement?",
        "ground_truth": "The parties are ABC Corporation as the Client and XYZ Legal Services as the Provider."
    },
    {
        "question": "What law governs this agreement?",
        "ground_truth": "This agreement is governed by the laws of the State of California."
    },
    {
        "question": "What must the client pay upon termination?",
        "ground_truth": "The client must pay all outstanding invoices upon termination."
    },
    {
        "question": "When was this agreement entered into?",
        "ground_truth": "This agreement was entered into as of January 1, 2024."
    },
    {
        "question": "What type of information must be kept confidential?",
        "ground_truth": "Both parties must keep all shared information strictly confidential."
    }
]


def run_rag_for_evaluation(question: str, retriever, llm):
    """
    Run RAG pipeline and return both answer and contexts.

    RAGAS needs three things per question:
    1. The question
    2. The generated answer (from our RAG system)
    3. The retrieved contexts (list of strings)

    Why return contexts separately?
    RAGAS uses contexts to measure faithfulness
    (is the answer grounded in what we retrieved?)
    and context metrics (did we retrieve the right stuff?)

    Args:
        question: Test question string
        retriever: Our FAISS retriever
        llm: Our GPT model

    Returns:
        Tuple of (answer string, list of context strings)
    """
    # Get retrieved documents
    docs = retriever.invoke(question)

    # Extract context strings for RAGAS
    contexts = [doc.page_content for doc in docs]

    # Build and run chain
    chain = build_rag_chain(retriever, llm, "general")
    answer = chain.invoke(question)

    return answer, contexts


def prepare_ragas_dataset(test_data, retriever, llm):
    """
    Run all test questions through RAG and prepare RAGAS dataset.

    RAGAS expects a HuggingFace Dataset with these columns:
    - question: the question string
    - answer: our RAG system's answer
    - contexts: list of retrieved context strings
    - ground_truth: the correct answer

    Args:
        test_data: List of question/ground_truth dictionaries
        retriever: Our FAISS retriever
        llm: Our GPT model

    Returns:
        HuggingFace Dataset ready for RAGAS evaluation
    """
    questions = []
    answers = []
    contexts = []
    ground_truths = []

    print(f"Running {len(test_data)} test questions through RAG...")
    print("This will make API calls — may take 30-60 seconds\n")

    for i, item in enumerate(test_data):
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"[{i+1}/{len(test_data)}] {question}")

        try:
            answer, context = run_rag_for_evaluation(
                question, retriever, llm
            )

            questions.append(question)
            answers.append(answer)
            contexts.append(context)
            ground_truths.append(ground_truth)

            print(f"         ✅ Answer generated")

        except Exception as e:
            print(f"         ❌ Error: {e}")
            continue

    # Create HuggingFace Dataset
    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    })

    return dataset


def run_evaluation(dataset, llm, embeddings_model):
    """
    Run RAGAS evaluation on our prepared dataset.

    Metrics explained:
    - faithfulness: Is answer grounded in retrieved context?
    - answer_relevancy: Does answer address the question?
    - context_precision: Are retrieved chunks relevant?
    - context_recall: Did we retrieve all needed chunks?

    Args:
        dataset: HuggingFace Dataset from prepare_ragas_dataset
        llm: LLM for RAGAS to use internally
        embeddings_model: Embeddings for RAGAS to use internally

    Returns:
        RAGAS results dictionary
    """
    print("\nRunning RAGAS evaluation...")
    print("RAGAS uses GPT internally to judge answer quality")
    print("This may take 1-2 minutes...\n")

    # RAGAS needs LangChain compatible models
    ragas_llm = llm
    ragas_embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Run evaluation with all four metrics
    results = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ],
        llm=ragas_llm,
        embeddings=ragas_embeddings
    )

    return results


def print_evaluation_report(results, dataset):
    """
    Print a comprehensive evaluation report.

    Args:
        results: RAGAS results
        dataset: Our test dataset for detailed analysis
    """
    print("\n" + "="*60)
    print("RAGAS EVALUATION REPORT")
    print("="*60)

    # Overall scores
    print("\n📊 OVERALL SCORES:")
    print("-"*40)

    # RAGAS returns a ResultsDataset object
    # We need to convert to pandas and get mean scores
    results_df = results.to_pandas()

    scores = {
        "Faithfulness": float(results_df["faithfulness"].mean()),
        "Answer Relevancy": float(results_df["answer_relevancy"].mean()),
        "Context Precision": float(results_df["context_precision"].mean()),
        "Context Recall": float(results_df["context_recall"].mean())
    }

    for metric, score in scores.items():
        bar = "█" * int(score * 20)
        spaces = "░" * (20 - int(score * 20))
        rating = "✅ GOOD" if score >= 0.8 else "⚠️ NEEDS WORK" if score >= 0.6 else "❌ POOR"
        print(f"{metric:<20} {score:.3f} |{bar}{spaces}| {rating}")

    # Interpretation
    print("\n📋 INTERPRETATION:")
    print("-"*40)

    if scores["Faithfulness"] >= 0.8:
        print("✅ Faithfulness: System answers are grounded in documents")
    else:
        print("⚠️  Faithfulness: System may be hallucinating — review prompts")

    if scores["Answer Relevancy"] >= 0.8:
        print("✅ Relevancy: Answers address the questions asked")
    else:
        print("⚠️  Relevancy: Answers may be off-topic — review prompts")

    if scores["Context Precision"] >= 0.8:
        print("✅ Precision: Retrieved chunks are relevant")
    else:
        print("⚠️  Precision: Retrieving irrelevant chunks — tune chunk size")

    if scores["Context Recall"] >= 0.8:
        print("✅ Recall: Retrieving all needed information")
    else:
        print("⚠️  Recall: Missing relevant chunks — increase K value")

    # Save results to file
    results_dict = {
        "scores": {k: float(v) for k, v in scores.items()},
        "num_questions": len(dataset)
    }

    with open("logs/evaluation_results.json", "w") as f:
        json.dump(results_dict, f, indent=2)

    print(f"\n💾 Results saved to logs/evaluation_results.json")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("RAG SYSTEM - DAY 10: RAGAS EVALUATION")
    print("="*60)

    # Initialize components
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

    # Step 1: Prepare evaluation dataset
    dataset = prepare_ragas_dataset(TEST_DATASET, retriever, llm)

    print(f"\nDataset prepared: {len(dataset)} questions")

    # Step 2: Run RAGAS evaluation
    results = run_evaluation(dataset, llm, embeddings_model)

    # Step 3: Print report
    print_evaluation_report(results, dataset)
