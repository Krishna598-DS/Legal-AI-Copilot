# main.py
# PURPOSE: FastAPI backend exposing our RAG system as a REST API
# Day 11: The engine room of our application

import os
import time
import shutil
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from src.ingestion.document_loader import load_document
from src.ingestion.text_chunker import chunk_documents
from src.ingestion.embeddings import create_embeddings
from src.ingestion.vector_store import (
    create_vector_store,
    load_vector_store,
    VECTOR_STORE_PATH
)
from src.retrieval.retriever import get_retriever
from src.llm.conversational_chain import ConversationalRAG

load_dotenv()

# ─────────────────────────────────────────────────
# APP INITIALIZATION
# ─────────────────────────────────────────────────

app = FastAPI(
    title="Legal Document Intelligence System",
    description="RAG-powered legal document analysis API",
    version="1.0.0"
)

# CORS middleware allows our frontend to talk to this API
# Without this, browsers block cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────
# GLOBAL STATE
# In production use a proper session store (Redis etc)
# For our app, module-level variables work fine
# ─────────────────────────────────────────────────

# These are initialized once and reused for every request
# Why? Creating embeddings model and LLM on every request
# would be slow and wasteful
embeddings_model = None
llm = None
conversational_rag = None
current_document = None


def initialize_models():
    """
    Load AI models once at startup.

    Why initialize at startup?
    Model initialization takes 1-2 seconds.
    We don't want users waiting for this on their first request.
    Loading once at startup means every request is fast.

    This is called during the startup event below.
    """
    global embeddings_model, llm

    print("Initializing AI models...")
    embeddings_model = create_embeddings()

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    print("AI models initialized successfully")


# ─────────────────────────────────────────────────
# PYDANTIC MODELS
# Define exact shape of request and response data
# FastAPI uses these for validation and documentation
# ─────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    """
    What the /ask endpoint expects to receive.
    Pydantic automatically validates these constraints.
    """
    question: str = Field(
        ...,  # ... means required
        min_length=3,
        max_length=1000,
        description="The question to ask about the document"
    )


class QuestionResponse(BaseModel):
    """What the /ask endpoint returns."""
    question: str
    answer: str
    question_type: str
    sources: list
    processing_time: float


class UploadResponse(BaseModel):
    """What the /upload endpoint returns."""
    message: str
    filename: str
    num_chunks: int
    status: str


class HealthResponse(BaseModel):
    """What the /health endpoint returns."""
    status: str
    model: str
    document_loaded: bool


# ─────────────────────────────────────────────────
# STARTUP EVENT
# Runs once when the API server starts
# ─────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """
    Initialize models when server starts.

    Also try to load existing vector store if one exists.
    This means if we restart the server, we don't lose
    previously uploaded documents.
    """
    global conversational_rag, current_document

    initialize_models()

    # Try to load existing vector store from disk
    try:
        vector_store = load_vector_store(embeddings_model)
        retriever = get_retriever(vector_store, k=3)
        conversational_rag = ConversationalRAG(retriever, llm)
        current_document = "Previously uploaded document"
        print("Loaded existing vector store from disk")
    except FileNotFoundError:
        print("No existing vector store — waiting for document upload")


# ─────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Why have this?
    Production systems need health checks so:
    - Load balancers know if the service is up
    - Monitoring systems can alert if it goes down
    - Deployment systems verify successful startup

    This is standard practice in production APIs.
    """
    return HealthResponse(
        status="healthy",
        model="gpt-4o-mini",
        document_loaded=conversational_rag is not None
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a legal document.

    Flow:
    1. Receive file from user
    2. Save to data/raw/
    3. Load and chunk the document
    4. Create vector store in FAISS
    5. Initialize conversational RAG
    6. Return success response

    Supports: .txt and .pdf files
    """
    global conversational_rag, current_document

    # Validate file type
    allowed_extensions = {".txt", ".pdf"}
    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not supported. Use .txt or .pdf"
        )

    # Save uploaded file to data/raw/
    # Replace spaces with underscores to avoid path issues
    safe_filename = file.filename.replace(" ", "_")
    upload_path = f"data/raw/{safe_filename}"

    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File saved: {upload_path}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )

    # Process document through RAG pipeline
    try:
        # Load document
        documents = load_document(upload_path)

        # Chunk document
        chunks = chunk_documents(documents)

        # Create vector store
        vector_store = create_vector_store(chunks, embeddings_model)

        # Create retriever
        retriever = get_retriever(vector_store, k=3)

        # Initialize conversational RAG
        conversational_rag = ConversationalRAG(retriever, llm)
        current_document = file.filename

        print(f"Document processed: {file.filename} → {len(chunks)} chunks")

        return UploadResponse(
            message="Document processed successfully",
            filename=safe_filename,
            num_chunks=len(chunks),
            status="ready"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the uploaded document.

    Flow:
    1. Validate question (Pydantic handles this automatically)
    2. Check document is loaded
    3. Run conversational RAG
    4. Return structured answer with timing

    Why track processing_time?
    Performance monitoring. If answers start taking
    too long, we know before users complain.
    """
    # Check document is loaded
    if conversational_rag is None:
        raise HTTPException(
            status_code=400,
            detail="No document uploaded. Please upload a document first."
        )

    # Track processing time
    start_time = time.time()

    try:
        # Run conversational RAG
        result = conversational_rag.ask(request.question)
        processing_time = time.time() - start_time

        # Get source information
        sources = []
        if current_document:
            sources.append({
                "filename": current_document,
                "type": "legal_document"
            })

        return QuestionResponse(
            question=result["question"],
            answer=result["answer"],
            question_type=result.get("question_type", "general"),
            sources=sources,
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}"
        )


@app.post("/conversation/reset")
async def reset_conversation():
    """
    Reset conversation history.

    Why expose this as an endpoint?
    When a user uploads a new document or wants to
    start fresh, they need to clear the conversation
    history. Without this, old context from previous
    questions pollutes new conversations.
    """
    if conversational_rag is None:
        raise HTTPException(
            status_code=400,
            detail="No active conversation to reset"
        )

    conversational_rag.reset_memory()

    return {"message": "Conversation history cleared successfully"}


@app.get("/")
async def root():
    """Root endpoint — basic info about the API."""
    return {
        "name": "Legal Document Intelligence System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "upload": "POST /upload",
            "ask": "POST /ask",
            "reset": "POST /conversation/reset"
        }
    }
