# AI Legal Copilot

**A production RAG system that turns dense legal documents into cited, trustworthy answers — and knows when *not* to answer.**

Upload a contract, lease, or NDA. Ask questions in plain English. Get grounded answers with source citations, a deterministic confidence score, and automatic safety guardrails that block anything that reads like legal advice rather than legal information.

**Live:** [https://legal-rag-t4gw.onrender.com](https://legal-rag-t4gw.onrender.com)

> Legal information, not legal advice — by design, not just by disclaimer.

---

## Why this project is interesting

Most RAG demos stop at "it retrieves and it answers." This one is built and benchmarked like a product that has to be *right*, not just plausible:

- **Hybrid retrieval, not a single vector search.** Dense (FAISS) + sparse (BM25) retrieval combined via a weighted ensemble — legal text is full of exact-match terms (defined terms, section numbers, dollar figures) that pure semantic similarity alone misses.
- **A real evaluation harness, not vibes.** Every retrieval and chunking decision is validated against a RAGAS-based benchmark — 141 hand-checked questions across 20 synthetic legal documents, scored on Faithfulness, Answer Relevancy, Context Precision, and Context Recall, run against the *actual* production answer path, not a mocked shortcut.
- **Deterministic trust scoring, not another LLM's opinion.** Confidence is computed from retrieval scores, citation coverage, and answer grounding — auditable and reproducible, never invented by the model itself.
- **Safety enforced in code, after generation.** A guardrail layer scrubs Legal-Advice-shaped claims from every response before it reaches the user — defense in depth, not just a system prompt asking nicely.
- **Evaluation infrastructure built for reliability.** Configurable concurrency, automatic retry logging, a data-integrity gate that refuses to silently report a corrupted benchmark run as valid, and checkpoint/resume for long evaluation jobs — survives real interruptions (rate limits, host sleep, session timeouts) with zero lost work.

### Results from the benchmark, not marketing copy

| Change | Result |
|---|---|
| Systematic chunk-size/overlap optimization (500 → 256 chars, benchmarked at every step) | **Faithfulness +8.8%** (0.826 → 0.899), **hard-question faithfulness +18%** (0.417 → 0.492), no recall regression |
| Eliminated a duplicate embedding call + an unnecessary LLM classification round-trip | **Mean response latency −43%** (2.88s → 1.64s) at matched retrieval config, zero quality regression |
| Persistent-disk-backed storage (fixing a redeploy-wipes-everything bug) | User accounts, documents, and vector indexes now survive redeployment — validated against a simulated production redeploy |

Full run history, per-question breakdowns, and methodology: [`evaluation/benchmark/results/`](evaluation/benchmark/results/).

---

## Architecture

```
Browser (Next.js static SPA)
   │  fetch, Bearer JWT
   ▼
FastAPI routes (thin, delegate immediately)
   ▼
Ingestion (upload → chunk → embed → FAISS, background job)
   ▼
Hybrid retrieval (dense FAISS + BM25 ensemble)
   ▼
LLM generation (prompt templates + safety preamble)
   ▼
Safety scrub + deterministic confidence scoring
   ▼
Response (answer + citations + confidence) → Browser
```

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind — static export, served same-origin by FastAPI |
| Backend | FastAPI, LangChain, SQLAlchemy |
| Retrieval | FAISS (dense) + BM25 (sparse) hybrid ensemble |
| LLM / Embeddings | OpenAI (`gpt-4o-mini`, `text-embedding-3-small`) |
| Evaluation | RAGAS + a custom production-path benchmark harness |
| Auth | JWT + Google Sign-In |
| Deployment | Docker, Render (persistent disk), GitHub Actions CI/CD |

---

## Evaluation & Benchmarking

The RAG pipeline has one source of truth for whether a change made answers *better* or *worse*: `backend/scripts/run_benchmark.py`, which runs the real production `/chat/ask` code path — including safety scrubbing and confidence scoring — against a versioned, checked-in dataset, and scores it with RAGAS.

```bash
PYTHONPATH=backend python backend/scripts/run_benchmark.py --dataset-dir evaluation/benchmark/datasets/v2
```

No retrieval, chunking, or prompt change ships without a before/after benchmark delta. Results are timestamped and never overwritten, so the full experiment history — including the ones that *didn't* work — is preserved in git, not just the winning configuration.

---

## Local Development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # set OPENAI_API_KEY + SECRET_KEY

# API (terminal 1)
export PYTHONPATH=$PWD/backend
bash backend/scripts/start.sh
# → http://127.0.0.1:8000

# UI (terminal 2)
cd web && npm install && npm run dev
# → http://127.0.0.1:3000
# web/.env.local: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Optional: build the static UI for same-origin serving by FastAPI:

```bash
cd web && npm run build:static   # writes ./frontend (gitignored)
```

## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`) on every PR and push to `main`:

1. **Frontend** — `npm ci`, lint, build
2. **Backend** — install deps, route smoke, pytest
3. **Docker** — build the production image

Render auto-deploys from `main` once CI is green (native GitHub integration, no manual deploy hook).

## Google Sign-In

1. [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials → **OAuth 2.0 Client ID** (Web)
2. Authorized JavaScript origins: `http://localhost:3000`, `http://127.0.0.1:8010`, and your production URL
3. Set `GOOGLE_CLIENT_ID` (and optional `GOOGLE_CLIENT_SECRET`) in `.env` / Render
4. UI shows **Sign in with Google** when `/auth/google/config` reports `enabled: true`

## Deploy

Render uses `Dockerfile` + `render.yaml`, including a persistent disk mounted at `/app/data` so the database, uploads, and vector indexes survive redeployment. Set `OPENAI_API_KEY`, `SECRET_KEY`, and `GOOGLE_CLIENT_ID` in the service environment.

## Layout

```
web/                            UI source (edit here)
backend/                        API + RAG pipeline (edit here)
evaluation/benchmark/           Versioned eval datasets + timestamped run history
.github/workflows/               CI/CD
Dockerfile                       production image
render.yaml                      Render config (persistent disk included)
```
