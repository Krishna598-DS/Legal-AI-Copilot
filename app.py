# app.py
# PURPOSE: Streamlit web interface for Legal Document Intelligence System
# Day 12: The face of our application

import streamlit as st
import requests
import json
import time
from pathlib import Path

# ─────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────

# Our FastAPI backend URL
API_URL = "http://localhost:8000"

# Page configuration — must be first Streamlit command
st.set_page_config(
    page_title="Legal Document Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────
# CUSTOM STYLING
# Streamlit allows custom CSS for professional look
# ─────────────────────────────────────────────────

st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a1a2e;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #16213e;
        margin-bottom: 2rem;
    }

    /* Answer box styling */
    .answer-box {
        background-color: #f0f7ff;
        border-left: 4px solid #0066cc;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }

    /* Source box styling */
    .source-box {
        background-color: #f9f9f9;
        border: 1px solid #ddd;
        padding: 0.8rem;
        border-radius: 0.3rem;
        font-size: 0.85rem;
        color: #666;
    }

    /* Question type badge */
    .badge-financial {
        background-color: #28a745;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        font-size: 0.75rem;
    }
    .badge-risk {
        background-color: #dc3545;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        font-size: 0.75rem;
    }
    .badge-general {
        background-color: #007bff;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        font-size: 0.75rem;
    }

    /* Chat message styling */
    .user-message {
        background-color: #e3f2fd;
        padding: 0.8rem 1rem;
        border-radius: 1rem 1rem 0.2rem 1rem;
        margin: 0.5rem 0;
        margin-left: 20%;
        text-align: right;
    }
    .assistant-message {
        background-color: #f5f5f5;
        padding: 0.8rem 1rem;
        border-radius: 1rem 1rem 1rem 0.2rem;
        margin: 0.5rem 0;
        margin-right: 20%;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #eee;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# These persist across Streamlit reruns
# ─────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "document_uploaded" not in st.session_state:
    st.session_state.document_uploaded = False

if "document_name" not in st.session_state:
    st.session_state.document_name = None

if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0

if "avg_response_time" not in st.session_state:
    st.session_state.avg_response_time = []


# ─────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────

def check_api_health():
    """Check if FastAPI backend is running."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False


def upload_document(file):
    """Upload document to FastAPI backend."""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(
            f"{API_URL}/upload",
            files=files,
            timeout=60
        )
        return response.json(), response.status_code
    except Exception as e:
        return {"detail": str(e)}, 500


def ask_question(question):
    """Send question to FastAPI backend."""
    try:
        response = requests.post(
            f"{API_URL}/ask",
            json={"question": question},
            timeout=30
        )
        return response.json(), response.status_code
    except Exception as e:
        return {"detail": str(e)}, 500


def reset_conversation():
    """Reset conversation on backend and clear frontend state."""
    try:
        requests.post(f"{API_URL}/conversation/reset", timeout=5)
    except:
        pass
    st.session_state.messages = []


# ─────────────────────────────────────────────────
# SIDEBAR
# Document upload and system info
# ─────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚖️ Legal AI Assistant")
    st.markdown("---")

    # API Health Status
    api_healthy = check_api_health()
    if api_healthy:
        st.success("🟢 System Online")
    else:
        st.error("🔴 System Offline — Start the API server")
        st.code("uvicorn src.api.main:app --reload --port 8000")
        st.stop()

    st.markdown("---")

    # Document Upload Section
    st.markdown("### 📄 Upload Document")
    st.markdown("Upload a legal document to analyze")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["txt", "pdf"],
        help="Supported formats: .txt, .pdf"
    )

    if uploaded_file is not None:
        if st.button("🚀 Process Document", type="primary"):
            with st.spinner("Processing document..."):
                result, status = upload_document(uploaded_file)

            if status == 200:
                st.session_state.document_uploaded = True
                st.session_state.document_name = uploaded_file.name
                st.session_state.messages = []
                st.success(f"✅ Document processed!")
                st.info(f"📊 Created {result.get('num_chunks', '?')} chunks")
            else:
                st.error(f"❌ Error: {result.get('detail', 'Unknown error')}")

    # Document Status
    if st.session_state.document_uploaded:
        st.markdown("---")
        st.markdown("### 📋 Current Document")
        st.info(f"📄 {st.session_state.document_name}")

        # Reset conversation button
        if st.button("🔄 Reset Conversation"):
            reset_conversation()
            st.success("Conversation cleared!")
            st.rerun()

    st.markdown("---")

    # System Info
    st.markdown("### ℹ️ System Info")
    st.markdown("""
    - **Model:** GPT-4o-mini
    - **Embeddings:** text-embedding-3-small
    - **Vector DB:** FAISS
    - **Framework:** LangChain
    """)

    # Stats
    if st.session_state.total_questions > 0:
        st.markdown("---")
        st.markdown("### 📊 Session Stats")
        st.metric("Questions Asked", st.session_state.total_questions)
        if st.session_state.avg_response_time:
            avg_time = sum(st.session_state.avg_response_time) / len(st.session_state.avg_response_time)
            st.metric("Avg Response Time", f"{avg_time:.2f}s")


# ─────────────────────────────────────────────────
# MAIN CONTENT AREA
# ─────────────────────────────────────────────────

# Header
st.markdown(
    '<div class="main-header">⚖️ Legal Document Intelligence System</div>',
    unsafe_allow_html=True
)

# Welcome message if no document uploaded
if not st.session_state.document_uploaded:
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <h2>📄</h2>
            <h4>Upload Document</h4>
            <p>Upload any legal contract or agreement from the sidebar</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <h2>💬</h2>
            <h4>Ask Questions</h4>
            <p>Ask anything about the document in plain English</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
            <h2>⚡</h2>
            <h4>Get Instant Answers</h4>
            <p>Receive accurate answers with source citations</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.info("👈 Upload a legal document from the sidebar to get started")

else:
    # ─────────────────────────────────────────────────
    # CHAT INTERFACE
    # Shows conversation history and accepts new questions
    # ─────────────────────────────────────────────────

    # Display conversation history
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant", avatar="⚖️"):
                st.write(message["content"])

                # Show metadata for assistant messages
                if "metadata" in message:
                    meta = message["metadata"]
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        q_type = meta.get("question_type", "general")
                        badge_class = f"badge-{q_type}"
                        st.markdown(
                            f'<span class="{badge_class}">📊 {q_type.upper()}</span>',
                            unsafe_allow_html=True
                        )

                    with col2:
                        proc_time = meta.get("processing_time", 0)
                        st.caption(f"⏱️ {proc_time}s")

                    with col3:
                        sources = meta.get("sources", [])
                        if sources:
                            st.caption(f"📄 {sources[0].get('filename', 'document')}")

    # Chat input
    if question := st.chat_input("Ask a question about your legal document..."):

        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": question
        })

        # Display user message
        with st.chat_message("user"):
            st.write(question)

        # Get answer from API
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Analyzing document..."):
                result, status = ask_question(question)

            if status == 200:
                answer = result.get("answer", "No answer received")
                st.write(answer)

                # Show metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    q_type = result.get("question_type", "general")
                    badge_class = f"badge-{q_type}"
                    st.markdown(
                        f'<span class="{badge_class}">📊 {q_type.upper()}</span>',
                        unsafe_allow_html=True
                    )
                with col2:
                    proc_time = result.get("processing_time", 0)
                    st.caption(f"⏱️ {proc_time}s")
                with col3:
                    sources = result.get("sources", [])
                    if sources:
                        st.caption(
                            f"📄 {sources[0].get('filename', 'document')}"
                        )

                # Update session stats
                st.session_state.total_questions += 1
                st.session_state.avg_response_time.append(
                    result.get("processing_time", 0)
                )

                # Add assistant message to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "metadata": result
                })

            else:
                error_msg = result.get("detail", "Unknown error occurred")
                st.error(f"❌ Error: {error_msg}")

    # Quick question buttons for common queries
    st.markdown("---")
    st.markdown("**💡 Quick Questions:**")

    col1, col2, col3, col4 = st.columns(4)

    quick_questions = [
        "What is the payment amount?",
        "What is the late payment penalty?",
        "How to terminate this contract?",
        "Who are the parties involved?"
    ]

    for col, question in zip([col1, col2, col3, col4], quick_questions):
        with col:
            if st.button(question, use_container_width=True):
                # Trigger the same flow as typing a question
                st.session_state.messages.append({
                    "role": "user",
                    "content": question
                })

                with st.spinner("Analyzing..."):
                    result, status = ask_question(question)

                if status == 200:
                    answer = result.get("answer", "")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "metadata": result
                    })
                    st.session_state.total_questions += 1
                    st.session_state.avg_response_time.append(
                        result.get("processing_time", 0)
                    )

                st.rerun()
