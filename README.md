# ⚖️ Legal Document Intelligence System

A production-grade Retrieval Augmented Generation (RAG) system
for intelligent legal document analysis. Upload any legal contract
and ask questions in plain English — get accurate, cited answers
powered by GPT-4o-mini.

## 🎯 Live Demo
[Click here to try the live app](your-streamlit-url-here)

Upload a legal contract → Ask questions → Get instant answers

## 🏗️ Architecture

Document Upload (PDF/TXT)
↓
Text Chunking (RecursiveCharacterTextSplitter)
↓
Embeddings (OpenAI text-embedding-3-small, 1536 dimensions)
↓
Vector Storage (FAISS)
↓
Semantic Retrieval (Cosine Similarity Search)
↓
Smart Prompt Selection (Financial / Risk / General)
↓
Answer Generation (GPT-4o-mini, temperature=0)
↓
Structured Response with Source Citation

## ✨ Features

- **Multi-format Support** — PDF and TXT documents
- **Semantic Search** — Finds relevant clauses by meaning not keywords
- **Smart Routing** — Automatically selects specialized prompt templates
- **Conversational Memory** — Follow-up questions maintain context
- **Hallucination Prevention** — Answers grounded strictly in document
- **Source Attribution** — Every answer cites its source section
- **REST API** — Full FastAPI backend with auto-generated docs
- **Interactive UI** — Streamlit chat interface

## 📊 Evaluation Results (RAGAS)

| Metric | Score | Status |
|--------|-------|--------|
| Faithfulness | 0.942 | ✅ Excellent |
| Context Precision | 0.950 | ✅ Excellent |
| Context Recall | 1.000 | ✅ Perfect |
| Answer Relevancy | 0.799 | ✅ Good |

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | GPT-4o-mini |
| Embeddings | text-embedding-3-small (1536 dims) |
| Vector DB | FAISS |
| Framework | LangChain 0.3.7 |
| Backend API | FastAPI |
| Frontend | Streamlit |
| Evaluation | RAGAS |
| PDF Parsing | PyMuPDF |

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/Krishna598-DS/legal-rag-system.git
cd legal-rag-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
echo "OPENAI_API_KEY=your-key-here" > .env
```

### Run the Application

```bash
# Option 1: Streamlit only (recommended)
streamlit run streamlit_app.py

# Option 2: Full stack (API + UI)
# Terminal 1
uvicorn src.api.main:app --reload --port 8000

# Terminal 2
streamlit run app.py
```

### Run Evaluation

```bash
python -m src.evaluation.evaluator
```

## 📁 Project Structure

legal-rag/
├── src/
│   ├── ingestion/
│   │   ├── document_loader.py    # PDF + TXT loading
│   │   ├── text_chunker.py       # Smart chunking
│   │   ├── embeddings.py         # OpenAI embeddings
│   │   └── vector_store.py       # FAISS operations
│   ├── retrieval/
│   │   └── retriever.py          # Semantic search
│   ├── llm/
│   │   ├── llm_chain.py          # Basic RAG chain
│   │   ├── rag_chain.py          # LCEL chain
│   │   ├── prompt_templates.py   # Smart prompts
│   │   └── conversational_chain.py # Memory
│   ├── api/
│   │   └── main.py               # FastAPI backend
│   └── evaluation/
│       └── evaluator.py          # RAGAS metrics
├── data/
│   ├── raw/                      # Uploaded documents
│   └── processed/                # FAISS index
├── logs/                         # Evaluation results
├── streamlit_app.py              # Deployment UI
├── app.py                        # Local UI
├── requirements.txt
└── README.md

## 🧠 Key Design Decisions

**Why FAISS over Pinecone?**
FAISS runs locally with zero infrastructure. For this scale
it provides millisecond search with no cost. Production
migration requires changing one line — LangChain abstracts
the interface.

**Why GPT-4o-mini over GPT-4o?**
Legal Q&A is a retrieval-grounded task. The model reads
provided context and summarizes — it doesn't need to reason
from scratch. GPT-4o-mini achieves equivalent quality at
10x lower cost for this use case.

**Why temperature=0?**
Legal documents require deterministic answers. The same
question must always produce the same answer. Temperature=0
eliminates randomness completely.

**Why chunking at 500 characters?**
Legal clauses average 200-400 words. 500 characters keeps
related terms together while remaining small enough for
precise retrieval. Validated by 0.950 context precision score.

## 📈 Future Improvements

- [ ] Multi-document support (compare multiple contracts)
- [ ] Table extraction from PDFs
- [ ] Citation with exact page numbers
- [ ] User authentication
- [ ] PostgreSQL + pgvector for production scale
- [ ] Streaming responses

## 👨‍💻 Author

Built as a portfolio project demonstrating production-grade
Gen AI engineering skills including RAG architecture,
prompt engineering, evaluation, and full-stack deployment.
