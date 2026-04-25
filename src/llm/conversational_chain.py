# conversational_chain.py
# PURPOSE: Add conversation memory to our RAG chain
# Day 9: Conversational AI with context awareness

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from src.ingestion.document_loader import load_document
from src.ingestion.text_chunker import chunk_documents
from src.ingestion.embeddings import create_embeddings
from src.ingestion.vector_store import (
    load_vector_store,
    create_vector_store
)
from src.retrieval.retriever import get_retriever
from src.llm.rag_chain import format_docs

load_dotenv()


def create_conversational_chain(retriever, llm):
    """
    Build a conversational RAG chain with two stages:

    STAGE 1 - Query Rewriter:
    Takes conversation history + new question
    Rewrites question into standalone version
    Example: "What about that?" → "What are the payment penalty terms?"

    STAGE 2 - Answer Generator:
    Takes standalone question + retrieved context + history
    Generates answer that references conversation naturally

    Why two stages?
    The retriever needs a clear standalone question to search effectively.
    The answer generator needs history to maintain conversational tone.
    These are different needs requiring different prompts.

    Args:
        retriever: Our FAISS retriever
        llm: Our GPT model

    Returns:
        Tuple of (contextualize_chain, answer_chain)
    """

    # ─────────────────────────────────────────
    # STAGE 1: QUERY REWRITER
    # Converts follow-up questions into standalone questions
    # ─────────────────────────────────────────

    contextualize_system_prompt = """You are a query rewriter for a legal document Q&A system.

Your job is to take a conversation history and a follow-up question,
then rewrite the follow-up question to be completely standalone.

The standalone question must make sense WITHOUT reading the conversation history.

RULES:
- If the question is already standalone, return it unchanged
- If the question references something from history, include that context
- Keep the rewritten question concise and clear
- Do NOT answer the question — only rewrite it

Examples:
History: "Q: What is the payment amount? A: $10,000 per month"
Follow-up: "What happens if that is late?"
Rewritten: "What happens if the $10,000 monthly payment is late?"

History: "Q: Who are the parties? A: ABC Corp and XYZ Legal"
Follow-up: "What are their obligations?"
Rewritten: "What are the obligations of ABC Corporation and XYZ Legal Services?"
"""

    contextualize_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_system_prompt),
        MessagesPlaceholder("chat_history"),  # Insert conversation history here
        ("human", "{input}")                  # The new follow-up question
    ])

    # Query rewriter chain
    # Takes history + question → returns rewritten standalone question
    contextualize_chain = contextualize_prompt | llm | StrOutputParser()

    # ─────────────────────────────────────────
    # STAGE 2: ANSWER GENERATOR
    # Answers the standalone question using retrieved context
    # ─────────────────────────────────────────

    answer_system_prompt = """You are a senior legal document analyst with 20 years of experience.

Answer questions about legal documents accurately and clearly.

STRICT RULES:
1. Answer ONLY using the provided document context
2. If information is not in the context, say: "This information is not found in the provided document."
3. Always cite the specific section your answer comes from
4. Be conversational — you can reference previous answers naturally
5. If the user references something from earlier in conversation, acknowledge it

CONTEXT FROM DOCUMENT:
{context}"""

    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", answer_system_prompt),
        MessagesPlaceholder("chat_history"),  # Conversation history for context
        ("human", "{input}")                  # The standalone question
    ])

    # Answer chain
    # Takes context + history + question → returns answer
    answer_chain = answer_prompt | llm | StrOutputParser()

    return contextualize_chain, answer_chain


class ConversationalRAG:
    """
    Complete conversational RAG system with memory.

    Why a class instead of functions?
    We need to maintain state between calls — specifically
    the chat_history list that grows with each exchange.
    A class is the natural Python pattern for stateful systems.

    In our FastAPI backend each user session will get
    their own ConversationalRAG instance.
    """

    def __init__(self, retriever, llm):
        """
        Initialize with retriever and LLM.
        Creates empty conversation history.
        """
        self.retriever = retriever
        self.llm = llm
        self.chat_history = []  # Stores HumanMessage and AIMessage objects

        # Build both chains
        self.contextualize_chain, self.answer_chain = \
            create_conversational_chain(retriever, llm)

        print("ConversationalRAG initialized")
        print(f"Memory: conversation window active")

    def ask(self, question: str) -> dict:
        """
        Ask a question with full conversation context.

        Flow:
        1. If history exists, rewrite question to be standalone
        2. Retrieve relevant chunks using standalone question
        3. Generate answer using context + history
        4. Save exchange to history
        5. Return answer with metadata

        Args:
            question: User's question (can be a follow-up)

        Returns:
            Dictionary with answer and metadata
        """

        print(f"\n{'='*60}")
        print(f"USER: {question}")

        # Step 1: Rewrite question if we have history
        if self.chat_history:
            print("Rewriting question with conversation context...")
            standalone_question = self.contextualize_chain.invoke({
                "input": question,
                "chat_history": self.chat_history
            })
            print(f"Standalone question: {standalone_question}")
        else:
            # First question — no history to contextualize
            standalone_question = question
            print("First question — no rewriting needed")

        # Step 2: Retrieve relevant chunks using standalone question
        print("Retrieving relevant chunks...")
        docs = self.retriever.invoke(standalone_question)
        context = format_docs(docs)

        # Step 3: Generate answer with full context
        print("Generating answer...")
        answer = self.answer_chain.invoke({
            "input": standalone_question,
            "context": context,
            "chat_history": self.chat_history
        })

        # Step 4: Save this exchange to history
        # HumanMessage = what user asked (original, not rewritten)
        # AIMessage = what system answered
        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))

        # Keep only last 6 messages (3 exchanges) to control token usage
        # This is our window memory implementation
        if len(self.chat_history) > 6:
            self.chat_history = self.chat_history[-6:]
            print("Memory window: kept last 3 exchanges")

        print(f"\nASSISTANT: {answer}")

        return {
            "question": question,
            "standalone_question": standalone_question,
            "answer": answer,
            "history_length": len(self.chat_history)
        }

    def reset_memory(self):
        """Clear conversation history — start fresh."""
        self.chat_history = []
        print("Conversation memory cleared")

    def show_history(self):
        """Display current conversation history."""
        print(f"\n--- CONVERSATION HISTORY ({len(self.chat_history)} messages) ---")
        for msg in self.chat_history:
            role = "USER" if isinstance(msg, HumanMessage) else "AI"
            print(f"{role}: {msg.content[:100]}...")


if __name__ == "__main__":
    print("="*60)
    print("RAG SYSTEM - DAY 9: CONVERSATIONAL MEMORY")
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

    # Create conversational RAG instance
    rag = ConversationalRAG(retriever, llm)

    print("\n--- CONVERSATION 1: FOLLOW-UP QUESTIONS ---")

    # Question 1: Standalone
    result1 = rag.ask("What is the monthly payment amount?")

    # Question 2: References Q1 with "that"
    result2 = rag.ask("What happens if that is paid late?")

    # Question 3: References previous context
    result3 = rag.ask("And how long must we keep that penalty information confidential?")

    # Show memory state
    rag.show_history()

    print("\n--- CONVERSATION 2: AFTER MEMORY RESET ---")
    rag.reset_memory()

    # This should fail gracefully without memory
    result4 = rag.ask("What happens if that is paid late?")
    print("\nNote: Without memory, vague questions get generic answers")
