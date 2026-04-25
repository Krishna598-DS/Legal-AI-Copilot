# streamlit_app.py
# PURPOSE: Standalone Streamlit app for deployment
# This version embeds RAG logic directly
# No separate FastAPI server needed

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# ─────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────

st.set_page_config(
    page_title="Legal Document Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a1a2e;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #16213e;
        margin-bottom: 2rem;
    }
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
# SESSION STATE
# ─────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "rag_ready" not in st.session_state:
    st.session_state.rag_ready = False
if "document_name" not in st.session_state:
    st.session_state.document_name = None
if "conversational_rag" not in st.session_state:
    st.session_state.conversational_rag = None
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0


# ─────────────────────────────────────────────────
# RAG INITIALIZATION
# ─────────────────────────────────────────────────

@st.cache_resource
def get_llm():
    """
    Initialize LLM once and cache it.

    @st.cache_resource caches the object across all users
    and reruns. Without this, we'd create a new LLM
    connection on every page interaction.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found!")
        st.stop()

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=api_key
    )


def process_uploaded_file(uploaded_file):
    """
    Process uploaded file through RAG pipeline.
    Returns ConversationalRAG instance ready for questions.
    """
    from src.ingestion.document_loader import load_document
    from src.ingestion.text_chunker import chunk_documents
    from src.ingestion.embeddings import create_embeddings
    from src.ingestion.vector_store import create_vector_store
    from src.retrieval.retriever import get_retriever
    from src.llm.conversational_chain import ConversationalRAG

    # Save uploaded file temporarily
    temp_dir = Path("data/raw")
    temp_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = uploaded_file.name.replace(" ", "_")
    temp_path = temp_dir / safe_filename

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    # Run through pipeline
    documents = load_document(str(temp_path))
    chunks = chunk_documents(documents)

    embeddings_model = create_embeddings()
    vector_store = create_vector_store(chunks, embeddings_model)
    retriever = get_retriever(vector_store, k=3)

    llm = get_llm()
    rag = ConversationalRAG(retriever, llm)

    return rag, len(chunks)


# ─────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚖️ Legal AI Assistant")
    st.markdown("---")

    # API Key input for deployed version
    # When deployed, users can enter their own key
    if not os.getenv("OPENAI_API_KEY"):
        st.markdown("### 🔑 OpenAI API Key")
        api_key = st.text_input(
            "Enter your OpenAI API key",
            type="password",
            help="Your key is never stored"
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            st.success("API key set!")
        else:
            st.warning("Enter API key to continue")
            st.stop()

    st.markdown("### 📄 Upload Document")

    uploaded_file = st.file_uploader(
        "Choose a legal document",
        type=["txt", "pdf"],
        help="Supports PDF and TXT files"
    )

    if uploaded_file is not None:
        if st.button("🚀 Process Document", type="primary"):
            with st.spinner("Processing document..."):
                try:
                    rag, num_chunks = process_uploaded_file(
                        uploaded_file
                    )
                    st.session_state.conversational_rag = rag
                    st.session_state.rag_ready = True
                    st.session_state.document_name = uploaded_file.name
                    st.session_state.messages = []
                    st.success(f"✅ Ready!")
                    st.info(f"📊 {num_chunks} chunks created")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    if st.session_state.rag_ready:
        st.markdown("---")
        st.markdown("### 📋 Current Document")
        st.info(f"📄 {st.session_state.document_name}")

        if st.button("🔄 Reset Conversation"):
            st.session_state.messages = []
            if st.session_state.conversational_rag:
                st.session_state.conversational_rag.reset_memory()
            st.success("Cleared!")
            st.rerun()

    st.markdown("---")
    st.markdown("### ℹ️ System Info")
    st.markdown("""
    - **Model:** GPT-4o-mini
    - **Embeddings:** text-embedding-3-small
    - **Vector DB:** FAISS
    - **Framework:** LangChain
    """)

    if st.session_state.total_questions > 0:
        st.markdown("---")
        st.markdown("### 📊 Session Stats")
        st.metric(
            "Questions Asked",
            st.session_state.total_questions
        )


# ─────────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────────

st.markdown(
    '<div class="main-header">⚖️ Legal Document Intelligence System</div>',
    unsafe_allow_html=True
)

if not st.session_state.rag_ready:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <h2>📄</h2>
            <h4>Upload Document</h4>
            <p>Upload any legal contract or agreement</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <h2>💬</h2>
            <h4>Ask Questions</h4>
            <p>Ask anything in plain English</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
            <h2>⚡</h2>
            <h4>Instant Answers</h4>
            <p>Get answers with source citations</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.info("👈 Upload a document from the sidebar to begin")

else:
    # Display conversation history
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant", avatar="⚖️"):
                st.write(message["content"])
                if "time" in message:
                    st.caption(f"⏱️ {message['time']}s")

    # Chat input
    if question := st.chat_input(
        "Ask a question about your legal document..."
    ):
        # Show user message
        st.session_state.messages.append({
            "role": "user",
            "content": question
        })

        with st.chat_message("user"):
            st.write(question)

        # Get answer
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Analyzing document..."):
                import time
                start = time.time()
                result = st.session_state.conversational_rag.ask(
                    question
                )
                elapsed = round(time.time() - start, 2)

            answer = result["answer"]
            st.write(answer)
            st.caption(f"⏱️ {elapsed}s")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "time": elapsed
            })
            st.session_state.total_questions += 1

    # Quick questions
    if st.session_state.rag_ready:
        st.markdown("---")
        st.markdown("**💡 Quick Questions:**")

        col1, col2, col3, col4 = st.columns(4)
        quick_questions = [
            "What is the payment amount?",
            "What is the late payment penalty?",
            "How to terminate this contract?",
            "Who are the parties involved?"
        ]

        for col, q in zip([col1, col2, col3, col4], quick_questions):
            with col:
                if st.button(q, use_container_width=True):
                    import time
                    st.session_state.messages.append({
                        "role": "user",
                        "content": q
                    })
                    start = time.time()
                    result = st.session_state.conversational_rag.ask(q)
                    elapsed = round(time.time() - start, 2)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "time": elapsed
                    })
                    st.session_state.total_questions += 1
                    st.rerun()
