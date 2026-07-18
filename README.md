# AI Legal Copilot

**Understand contracts. Detect risks. Walk into legal conversations prepared.**

A full-stack, multi-user RAG product that turns uploaded legal documents into cited explanations, risk highlights, consultation briefings, and expert-category recommendations — with confidence scoring and a legal AI safety layer.

### Live demo
[Try the live app](https://legal-rag-kk.streamlit.app/)

> This project is **legal information**, not legal advice. It does not create an attorney–client relationship.

---

### Built by [Krishna Kishore](https://github.com/Krishna598-DS)

Open to roles in **AI Engineering · Backend / Full-Stack · Applied LLM / RAG · Product Engineering**.

| | |
|---|---|
| **Email** | [krishnakishoregedela@gmail.com](mailto:krishnakishoregedela@gmail.com) |
| **GitHub** | [github.com/Krishna598-DS](https://github.com/Krishna598-DS) |
| **This repo** | [github.com/Krishna598-DS/legal-rag](https://github.com/Krishna598-DS/legal-rag) |

Prefer a quick chat? Email me — happy to walk through architecture, demos, or trade-offs.

---

## Why this project stands out

Most “PDF chatbots” stop at Q&A. This one is productized as a **consumer-facing legal copilot**:

- **Grounded answers** with page citations — not free-form hallucination theater
- **Measurable confidence** on AI outputs (High / Medium / Low)
- **Safety guardrails** that keep the product in “legal information,” not unauthorized advice
- **End-to-end workflow**: upload → explain → risk scan → consult prep → find the right *type* of professional
- **Multi-user isolation**, JWT auth, role-based dashboards, admin tools, deploy configs, and tests

If you hire for engineers who ship **LLM systems with product judgment**, this repo is a strong signal.

---

## What it does (working functionality)

| Capability | What users get |
|---|---|
| **Private document workspace** | Upload PDF/TXT; chunk, embed, and index per user |
| **Cited Q&A** | Ask questions (incl. streaming); answers cite source pages |
| **Explain this document** | Plain-language overview: parties, dates, obligations, risks — with citations |
| **Detect risks** | Severity-ranked highlights (e.g. renewal, liability, penalties) grounded in the doc |
| **Compare contracts** | Side-by-side comparison of payment, termination, liability, and more |
| **Prepare for consultation** | Cited briefing (facts, timeline, risks, questions) + **PDF download** |
| **Find a professional** | Recommends an **expert category** (not a named lawyer) + curated local directory search |
| **Role-aware home** | Dashboards for Individual, Lawyer, CA, Business Owner, HR, Student |
| **Admin** | Usage stats, user controls, professionals directory management |

---

## Architecture at a glance

```
User (Web UI)
    │
    ▼
FastAPI  ── JWT auth, rate limits, health checks
    │
    ├── Documents  → PyMuPDF → chunks → OpenAI embeddings → FAISS (+ BM25 hybrid)
    ├── Chat / Explain / Risks / Compare / Consultation / Expert
    ├── Confidence scoring + safety guardrails
    └── SQLite (default) · Postgres optional · Redis optional
```

**Stack:** Python · FastAPI · LangChain · OpenAI · FAISS · SQLAlchemy · JWT · vanilla HTML/CSS/JS · pytest · Docker · Render / Fly / Hugging Face Spaces

---

## Product principles baked into the code

1. **Citations first** — answers should point back to the document  
2. **Confidence is visible** — weak retrieval/grounding surfaces as Medium/Low, not fake certainty  
3. **Safety by design** — prompts + output checks discourage court predictions, “sue now,” or replacing a lawyer  
4. **Privacy** — documents and chats are scoped to the authenticated user  

Details: [`docs/confidence-scoring.md`](docs/confidence-scoring.md) · [`docs/legal-ai-safety.md`](docs/legal-ai-safety.md)

---

## Quick start (local)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # set OPENAI_API_KEY + SECRET_KEY

bash backend/scripts/start.sh
# → http://127.0.0.1:8000
```

Optional Streamlit UI: `streamlit run frontend/streamlit/app.py`

### Tests

```bash
export PYTHONPATH=$PWD/backend FRONTEND_DIR=$PWD/frontend
pytest -q backend/tests
```

### Deploy

Hosting can be near-$0 (Render / Fly / HF Spaces); OpenAI usage is billed separately.  
See `render.yaml`, `fly.toml`, `Dockerfile`, `README_SPACE.md`.

---

## Repo layout

```
frontend/     Consumer web UI (+ optional Streamlit)
backend/      FastAPI, RAG services, safety, tests, scripts
docs/         Confidence scoring & legal AI safety notes
data/         SQLite, uploads, indexes (local)
```

---

## Looking for your next engineer?

I’m Krishna Kishore — I build applied AI systems that are **useful, grounded, and shippable**.

If you’re hiring for backend, AI/ML product, or full-stack roles, I’d love to connect:

**[krishnakishoregedela@gmail.com](mailto:krishnakishoregedela@gmail.com?subject=AI%20Legal%20Copilot%20—%20let’s%20talk)** · **[GitHub](https://github.com/Krishna598-DS)** · **[This project](https://github.com/Krishna598-DS/legal-rag)**
