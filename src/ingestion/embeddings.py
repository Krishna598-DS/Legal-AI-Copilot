# embeddings.py
# PURPOSE: Convert text chunks into numerical vectors (embeddings)
# This is Step 3 of our RAG pipeline: Chunks → Vectors

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from src.ingestion.document_loader import load_document
from src.ingestion.text_chunker import chunk_documents

# Load API key from .env file
load_dotenv()


def create_embeddings():
    """
    Create and return an OpenAI embeddings model.
    This model converts any text into a vector of 1536 numbers.

    Why we create this as a separate function:
    - We reuse this in multiple places (ingestion + retrieval)
    - If we switch embedding models later, we change it in ONE place only
    - This is called the DRY principle (Don't Repeat Yourself)
    """

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",  # Best cost/quality ratio
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    print("Embedding model loaded: text-embedding-3-small")
    print("Dimensions: 1536")

    return embeddings


def embed_text(text: str, embeddings_model) -> list:
    """
    Convert a single piece of text into a vector.

    Args:
        text: Any string of text
        embeddings_model: Our OpenAI embeddings model

    Returns:
        A list of 1536 floating point numbers
    """
    vector = embeddings_model.embed_query(text)
    return vector


def demonstrate_embeddings(embeddings_model):
    """
    Show embeddings in action — proves that similar text
    produces similar vectors and different text produces
    different vectors.
    """
    import numpy as np

    # Three test sentences
    sentence_1 = "What is the late payment penalty?"
    sentence_2 = "What happens if payment is overdue?"
    sentence_3 = "What is the governing law of this contract?"

    print("\nGenerating embeddings for 3 sentences...")
    vec_1 = embed_text(sentence_1, embeddings_model)
    vec_2 = embed_text(sentence_2, embeddings_model)
    vec_3 = embed_text(sentence_3, embeddings_model)

    print(f"\nSentence 1: '{sentence_1}'")
    print(f"Vector preview: {vec_1[:5]}...")
    print(f"Vector length: {len(vec_1)} dimensions")

    # Calculate similarity between sentences
    # Cosine similarity: 1.0 = identical meaning, 0.0 = completely different
    def cosine_similarity(a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    sim_1_2 = cosine_similarity(vec_1, vec_2)
    sim_1_3 = cosine_similarity(vec_1, vec_3)

    print(f"\n--- SIMILARITY SCORES ---")
    print(f"'{sentence_1}'")
    print(f"vs '{sentence_2}'")
    print(f"Similarity: {sim_1_2:.4f} (these mean similar things)")

    print(f"\n'{sentence_1}'")
    print(f"vs '{sentence_3}'")
    print(f"Similarity: {sim_1_3:.4f} (these mean different things)")

    print("\nHigher score = more similar meaning")
    print("This is exactly how our search will find relevant chunks!")


if __name__ == "__main__":
    # Step 1: Create the embedding model
    embeddings_model = create_embeddings()

    # Step 2: Demonstrate how embeddings work
    demonstrate_embeddings(embeddings_model)

    # Step 3: Show embeddings on our actual document chunks
    print("\n--- EMBEDDING OUR LEGAL DOCUMENT CHUNKS ---")
    documents = load_document("data/raw/sample_contract.txt")
    chunks = chunk_documents(documents)

    print(f"\nEmbedding {len(chunks)} chunks...")
    for i, chunk in enumerate(chunks):
        vector = embed_text(chunk.page_content, embeddings_model)
        print(f"Chunk {i+1}: {len(vector)} dimensional vector ✅")
        print(f"Content preview: {chunk.page_content[:80]}...")
