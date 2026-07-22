# AI Legal Copilot — CLAUDE.md

Onboarding guide for Claude Code sessions in this repository. Read this first. It covers what
README and the architecture docs don't: current-vs-target state, in-flight work, and the house
engineering philosophy. For setup/local-dev commands see `README.md`; for full architecture
rationale see the root design docs referenced throughout.

Last verified: **2026-07-22** (commit `3ae7f28`, branch `main`, plus uncommitted Google Sign-In work).

---

## Quick Session Context

*(This block reflects the latest session handoff. It changes often — [Current Project
Status](#current-project-status) below has the fuller history and completed-work record.)*

- **Current sprint:** Sprint 3 — Retrieval Optimization (chunk-size/overlap sweep **complete and
  shipped**; retrieval-K/hybrid-weight sweep, per `OPTIMIZATION_PLAN.md` Tasks 7-9, not yet started)
- **Branch:** `main`
- **Production retrieval config frozen this sprint:** `CHUNK_SIZE=256`, `CHUNK_OVERLAP=50`
  (changed from the original `500/50` — see Decision Log). Chosen after a full sweep across
  500/768/384/256 chunk sizes and a 50 vs. 75 overlap test at 256, all on the `v2` benchmark
  (141 samples, dataset unchanged throughout).
- **Latest benchmark** (run `20260722T153038Z`, dataset `v2`, 141 samples, config 256/75 — the
  losing overlap candidate; the winning `256/50` config's own run is `20260722T054227Z`):
  Faithfulness 0.899, Answer Relevancy 0.708, Context Precision 0.848, Context Recall 0.956,
  Hard-question Faithfulness 0.492 (vs. 0.417 at the original 500/50 baseline — the gap this
  sprint targeted). Full run history: `evaluation/benchmark/results/reports/`.
- **Current focus:**
  - Sprint 3's chunk-size/overlap work is done; next candidate step is the retrieval-depth/
    hybrid-weight sweep (`RETRIEVAL_K`, `HYBRID_DENSE_WEIGHT`/`HYBRID_BM25_WEIGHT`) per
    `OPTIMIZATION_PLAN.md` Tasks 7-9, or moving on to broader production-readiness work.
  - Maintain production behavior — no regressions to safety scrubbing, confidence scoring, or the
    answer format while tuning retrieval.
  - Benchmark every change — no retrieval/chunking/parameter change ships without a
    `run_benchmark.py` before/after delta.
  - **Benchmark harness is now checkpoint/resume-capable** (see `checkpoint.py`) — a long run
    interrupted mid-execution (session timeout, host sleep, rate-limit exhaustion) can be
    re-launched with the same config and picks up exactly where it left off, at per-sample
    granularity, with no re-work and no data loss. Validated against multiple real interruptions
    this sprint, not just a synthetic test.
- **Read before coding:**
  1. This file, in full.
  2. The latest benchmark report (path above).
  3. The relevant architecture doc (`OPTIMIZATION_PLAN.md` for retrieval/chunking work;
     others only if touching that subsystem) — only after 1 and 2, not instead of them.

---

## Project Overview

RAG product: upload a legal document (contract, lease, NDA) → cited, grounded Q&A, plus explain /
risk / consultation-prep / expert-category features on the same retrieval layer. Positioned as
**"legal information, not legal advice"** — this drives real decisions (safety guardrails,
disclaimer flow), not just copy. Full stack summary lives in `README.md`.

**Long-term vision** (per `PRODUCT_ARCHITECTURE.md`, `AUTH_ARCHITECTURE.md` — **design specs, not
implemented**): multi-provider AI routing, Postgres + Alembic, object-storage-backed indexes for
horizontal scaling, session-based auth with RBAC, subscriptions, enterprise SSO. These describe
where the system is going, not what's running. See [Roadmap](#roadmap).

---

## Tech Stack

Full dependency list: `backend/requirements.txt`, `web/package.json`. Notable facts not obvious
from those files:

| Layer | Detail worth knowing |
|---|---|
| Frontend | Next.js static export (`output: "export"`) served **same-origin by FastAPI**, not a separate host. One monolithic `AppShell` component, no client-side router. |
| Database | SQLite by default, `DATABASE_URL`-driven ("Postgres-ready" but **no Alembic/migration framework** — hand-written additive `ALTER TABLE` in `migrate_sqlite()`). |
| Vector store | FAISS, one flat index per `(user_id, document_id)` **on local disk**. Hybrid retrieval = FAISS + BM25 via LangChain `EnsembleRetriever`. |
| LLM/Embeddings | OpenAI only (`gpt-4o-mini`, `text-embedding-3-small`). `ChatOpenAI`/`OpenAIEmbeddings` instantiated directly at call sites — **no provider abstraction**. |
| Evaluation | RAGAS 0.2.6 + a custom harness in `backend/src/evaluation/benchmark/` — see [Evaluation & Benchmarking](#evaluation--benchmarking). |
| Deployment | Single Docker image + Render, GitHub Actions CI/CD gates every deploy. |

---

## High-Level Architecture

```
Browser (Next.js static SPA)
   │  fetch, Bearer JWT
   ▼
FastAPI routes (thin, delegate immediately)
   ▼
Service layer  →  Ingestion (upload → chunk → embed → FAISS, via BackgroundTasks)
   ▼
RAG orchestration (services/rag_service.py)
   ▼
Retrieval (hybrid dense FAISS + BM25, retrieval/retriever.py)
   ▼
LLM (llm/prompt_templates.py — general/financial/risk templates + safety preamble)
   ▼
Safety scrub + confidence score (safety/guardrails.py → services/confidence.py)
   ▼
Response (answer + citations + confidence) → Browser
```

Follow-up questions are rewritten to a standalone query (using chat history) before retrieval
runs — retrieval always operates on the contextualized query, never the raw turn.

**Module map** (`backend/src/`):

| Module | Owns |
|---|---|
| `api/routes/` | auth, documents, chat, account, orgs, professionals, admin, health — one thin router each |
| `auth/` | JWT issuance, schemas, persona normalization |
| `config/settings.py` | Single env-driven `Settings` object (pydantic-settings, `lru_cache`d) |
| `db/` | `database.py` (engine + `migrate_sqlite()`), `models.py` (ORM) |
| `ingestion/` | Document load → chunk (`RecursiveCharacterTextSplitter`, 500/50) → embed → FAISS persist |
| `retrieval/retriever.py` | Hybrid dense+BM25 `EnsembleRetriever` (0.6/0.4 weights), dense-only fallback |
| `llm/` | Prompt templates + question classifier; `rag_chain.py` is legacy (used only by the superseded `evaluator.py`) |
| `safety/` | Regex-based post-generation scrubbing of Legal-Advice-shaped claims + shared safety preamble |
| `services/` | `rag_service.py` (734 lines — cache, orchestration, safety/confidence, SSE streaming; **top refactor candidate**), `confidence.py` (deterministic scoring), per-feature `*_service.py`/`*_grounding.py`, `query_embedding_cache.py` |
| `directory/` | Professional-directory matching (`local` provider) |
| `observability/` | Structured `log_event` logging, contextvar-propagated request/user id |
| `errors/` | Typed exception hierarchy + centralized handlers, one JSON error shape |
| `evaluation/` | Legacy `evaluator.py` (superseded) + `evaluation/benchmark/` (current harness) |

---

## Repository Structure

Beyond what `README.md`'s Layout section already covers (`web/`, `backend/`, `Dockerfile`,
`render.yaml`):

- **`evaluation/benchmark/`** — data, not code: `datasets/<version>/` (manifest + fixture docs +
  JSON samples), `results/runs/` + `results/reports/` (timestamped, never overwritten),
  `.state/` (gitignored, isolated eval runtime). Harness code itself lives in
  `backend/src/evaluation/benchmark/`. See its own `README.md` for the sample schema.
- **`data/`, `logs/`** — gitignored runtime state (SQLite DB, uploads, FAISS indexes, app log) —
  **not durable storage today** (see [Known Technical Debt](#known-technical-debt)).
- **Root design docs** — target-architecture specifications:
  - `PRODUCT_ARCHITECTURE.md` — whole-system review, current-vs-2-3yr-target, priority-ranked
  - `AUTH_ARCHITECTURE.md`, `AUTH_FLOW.md`, `DATABASE_DESIGN.md`, `SECURITY_DESIGN.md`,
    `MIGRATION_PLAN.md` — target identity/session/RBAC/subscription model and migration path
  - `RAG_EVALUATION_ARCHITECTURE.md`, `OPTIMIZATION_PLAN.md` — evaluation/perf plans, **largely
    already implemented** (unlike the auth/db docs above)

**Critical caveat:** `PRODUCT_ARCHITECTURE.md` / `AUTH_*` / `DATABASE_DESIGN.md` /
`SECURITY_DESIGN.md` / `MIGRATION_PLAN.md` all self-label "design specification — not
implemented." Do not assume anything they describe (sessions table, refresh tokens, RBAC,
`UserContext`, `ModelRouter`, Alembic) exists — verify against `backend/src/db/models.py` and the
actual route/service files first.

---

## Development Principles & Coding Standards

- **Benchmark before optimizing, always.** Any retrieval/chunking/prompt/model change re-runs
  `backend/scripts/run_benchmark.py` and reports a before/after delta — no exceptions.
- **Trace every optimization to a concrete mechanism**, not a tuning guess (`OPTIMIZATION_PLAN.md`'s
  own discipline — cite the file/line affected).
- **Evaluate the real production path.** The legacy `evaluator.py` harness skipped safety
  scrubbing and confidence scoring — treated as a correctness bug, not an acceptable shortcut.
- **Prefer deterministic, auditable signals over LLM self-judgment** (`services/confidence.py`'s
  weighted formula, never LLM-invented) — trustable and unit-testable independent of RAGAS's own
  LLM judge.
- **Safety is enforced in code after generation**, not just prompted for — defense in depth.
- **Config flags survive their own resolution.** When benchmarking settles a question (e.g.
  `USE_LLM_CLASSIFIER`), change the default but keep the losing path available, not deleted.
- **Stay a modular monolith.** No microservice extraction until a real team-ownership,
  scaling-profile, or compliance-isolation trigger exists (`PRODUCT_ARCHITECTURE.md`).
- **Additive migrations, not rewrites** — new modules alongside old ones.
- **Treat benchmark samples like code** — reviewed in PRs, ground truth verified before merge,
  never silently edited/deleted once a run references them (supersede with a new id instead).
- **Routes stay thin**, business logic in `services/`; raise typed exceptions
  (`errors/exceptions.py`), never bare `HTTPException`, from inside services.
- **Structured logging only** — `log_event(logger, event, **fields)` with consistent field names;
  don't read `os.environ` directly (go through `config/settings.py`).
- **Comment the why, not the what** — follow the existing style in `settings.py` /
  `query_embedding_cache.py` (non-obvious constraints and benchmarking evidence, not restatement).

---

## Evaluation & Benchmarking

Two evaluation code paths exist — know which one you're looking at:

| | `evaluation/evaluator.py` (legacy) | `evaluation/benchmark/` (current) |
|---|---|---|
| Dataset | Hardcoded 10-question list | Versioned JSON, `evaluation/benchmark/datasets/<version>/` |
| Answer path | Non-conversational `rag_chain.py` — **skips safety + confidence** | Real `rag_service.ask_document` — what `/chat/ask` actually calls |
| Storage | Single overwritten file | Timestamped JSON + markdown report per run, never overwritten |
| In CI | No | No (manual invocation only) |

**Datasets:** `v1` (Sprint 1 baseline — 15 samples / 3 synthetic docs) and `v2` (current — **141
samples / 20 synthetic contract-type documents**, easy/medium/hard difficulty incl. deliberate
abstention cases). All fixtures synthetic, never real user data. Schema and sample-authoring rules:
`evaluation/benchmark/README.md`. Full design rationale, RAGAS metric ranges, and DB schema plan:
`RAG_EVALUATION_ARCHITECTURE.md`.

**Metrics per run:** RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall) +
custom instrumentation added in Sprint 2A (`evaluation/benchmark/instrumentation.py`): retrieval/
generation/embedding latency, token counts & cost (chat + embedding), embedding cache hit/miss
rate, and the product's own confidence score — enabling correlation against RAGAS's LLM-judged
faithfulness.

**Run it:** `PYTHONPATH=backend python backend/scripts/run_benchmark.py [--dataset-dir
evaluation/benchmark/datasets/v2]` (defaults to `v1`). Isolates itself from production data
(separate DB/uploads/indexes), ingests fixtures, runs every question through the real production
call, scores with RAGAS, and diffs against the most recent prior run **on the same dataset
version** (cross-version comparison is invalid — versions aren't score-comparable).

**Why this matters:** the RAG pipeline has essentially no other regression signal (see
[Known Technical Debt](#known-technical-debt) — test coverage is near zero). This harness is
currently the only way to know if a change made answers better or worse before a real user does.

---

## Current Project Status

**Completed:** core product (multi-user auth, upload/ingestion, hybrid RAG Q&A, explain/risk/
consultation/expert features + grounding checks, safety guardrails, confidence scoring,
professional directory, admin scaffolding); Next.js-on-FastAPI deployment + CI/CD; **Sprint 1** —
production-path benchmark harness replacing the divergent legacy evaluator, `v1` dataset, RAGAS
wired in; **Sprint 2** — `v2` dataset expansion to 141 samples/20 docs (merged 2026-07-22, PR #1);
**Sprint 2A** — token/cost instrumentation, duplicate query-embedding call eliminated
(`query_embedding_cache.py`), `USE_LLM_CLASSIFIER` defaulted off (keyword classifier matches LLM
routing at zero extra cost); **benchmark-harness robustness** — explicit `RunConfig(max_workers=4,
log_tenacity=True)` (was the unconfigured library default of 16 concurrent workers), a data-
integrity gate that marks a run `INVALID` if any RAGAS metric scores below 90% of samples instead
of silently reporting a plausible-looking mean over a handful of survivors, and full checkpoint/
resume support (`checkpoint.py`) so a multi-hour run survives interruption (session timeout, host
sleep, OpenAI rate-limit exhaustion — all observed and worked around this sprint) without redoing
completed work; **Sprint 3 chunk-size/overlap sweep** — see below, **shipped**.

**Current (uncommitted as of 2026-07-22):** Google Sign-In integration — `google-sign-in.tsx`,
`/auth/google/config` endpoint, `role` passthrough on registration, `auth-panel.tsx` wiring,
`GOOGLE_CLIENT_ID`/`SECRET` plumbed through `render.yaml`/`.env.example`.

**Sprint 3 result — production retrieval config changed.** Full chunk-size sweep (500 original
baseline → 768 → 384 → 256, holding `RETRIEVAL_K=3`, hybrid weights 0.6/0.4, and everything else
fixed) plus an overlap sweep at the winning size (50 vs. 75), all on the `v2` benchmark (141
samples each run). **`CHUNK_SIZE=256`, `CHUNK_OVERLAP=50` shipped as the new production default**
(was `500/50`) — see Decision Log for the full evidence trail.

**Latest benchmark** (run `20260722T054227Z`, dataset `v2`, 141 samples, 0 errors, k=3,
chunk **256/50** — the winning config, hybrid 0.6/0.4):

| Metric | Score | | Metric | Score |
|---|---|---|---|---|
| Faithfulness | 0.899 | | Context Precision | 0.848 |
| Answer Relevancy | 0.708 | | Context Recall | 0.956 |

Hard-question Faithfulness 0.492 (vs. 0.417 at the original 500/50 baseline — the gap Sprint 3
targeted; +18% relative). Mean e2e latency 1.73s; ~1111 tokens/question; ~$0.0002/request.
Original `500/50` baseline for reference: Faithfulness 0.826, Hard Faithfulness 0.417, Context
Precision 0.880, Context Recall 0.955, mean e2e 2.88s (that run's latency is not directly
comparable — it predates the Sprint 2A embedding-cache/classifier changes above). Full run
history, including the 768 and 384 intermediate points and the failed 256/75 overlap candidate:
`evaluation/benchmark/results/reports/`.

**Next** (per `OPTIMIZATION_PLAN.md`'s recommended order): Tasks 7–9 (`RETRIEVAL_K`/hybrid-weight
sweep) → Tasks 10–14 (chunk reordering, MMR experiment, context budget/dedup, prompt tightening,
experiment-time embedding cache) → or move on to broader production-readiness work (test coverage,
security hardening, deployment persistence) per `PRODUCT_ARCHITECTURE.md`'s priority ranking.

---

## Git Workflow

```
Feature branch → Benchmark (run_benchmark.py, report the delta) → PR
   → CI (frontend lint+build, backend smoke+pytest, Docker build)
   → Merge to main → Render deploy hook (only after CI is green)
```

Defined in `.github/workflows/ci-cd.yml`. Render auto-deploy should stay **off** so production
only updates after CI passes.

---

## Common Development Commands

Local setup (venv, `.env`, `npm install`, dev servers) is in `README.md` — not repeated here.

```bash
# Benchmark (see Evaluation & Benchmarking above)
PYTHONPATH=backend python backend/scripts/run_benchmark.py
PYTHONPATH=backend python backend/scripts/run_benchmark.py --dataset-dir evaluation/benchmark/datasets/v2

# Legacy evaluator (superseded — prefer run_benchmark.py)
PYTHONPATH=backend python -m src.evaluation.evaluator

# Tests / smoke checks
pytest -q backend/tests --tb=short         # 2 liveness/info smoke tests only
python backend/scripts/smoke_api.py        # route import + smoke
python backend/scripts/smoke_auth.py       # auth flow smoke
python backend/scripts/smoke_logging.py    # logging config smoke
```

---

## Known Technical Debt

Full detail and target fixes: `PRODUCT_ARCHITECTURE.md` (priorities as stated there).

| Area | Priority | Issue |
|---|---|---|
| Deployment persistence | **Resolved in code, pending deploy** | `render.yaml` now mounts a persistent disk at `/app/data` (covers the SQLite DB, uploads, and FAISS indexes — confirmed via a local Docker-volume test: user/document data and a working RAG answer all survived a simulated redeploy that previously wiped everything). Requires `plan: starter` (was `free`) — a real billing change that takes effect only once actually deployed to Render, not yet live. |
| Authentication | High | Single 24h JWT, `localStorage` (XSS-exposed), no refresh tokens/session revocation, `ADMIN_EMAILS` env-var allowlist instead of RBAC. |
| Testing coverage | High | Two liveness tests total; zero coverage on auth, ingestion, retrieval, RAG answers, safety, grounding. |
| AI provider coupling | High | `ChatOpenAI`/`OpenAIEmbeddings` instantiated directly at call sites — no router/interface. |
| Retrieval storage | High | FAISS indexes + uploads on local disk only — same loss risk as deployment persistence; blocks >1 API instance. |
| DB migrations | High | No Alembic; `migrate_sqlite()` swallows exceptions silently; Postgres has zero migration path despite being the stated target. |
| `rag_service.py` size | Medium | 734 lines, 5 concerns — first refactor split candidate. |
| Frontend architecture | Medium→High | One `AppShell`, ~15 `useState` hooks, no router — fine for one view, compounds with new features. |
| Observability | Medium | Console/local-file logs only; no metrics/traces/aggregation. |
| Evaluation not in CI | Medium | Harness is production-faithful but not automated — regressions ship silently. |
| Dev experience | Low | No task runner, pre-commit hooks, or ADR directory. |

---

## Roadmap

**Completed → Current → Next:** see [Current Project Status](#current-project-status) above.

**Future** (design-spec stage — `PRODUCT_ARCHITECTURE.md` Part 13 and companion docs):
persistent-disk/object-storage fix; Alembic + managed Postgres; session-based auth
(`sessions`/`identities`/`refresh_tokens`, RBAC, `UserContext`); `AIProvider`/`ModelRouter`
abstraction (gated on resolving today's provider coupling first); subscriptions/billing, feature
flags, org/SSO; evaluation-in-CI + full DB-backed results schema + dashboard; cross-provider RAGAS
comparison; a real backend test suite (unit → integration → evaluation-as-CI).

---

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-04-25/26 | Built as single-service FastAPI + LangChain + FAISS + SQLite | Fastest path for a single-founder stage |
| 2026-07-19 | Replaced vanilla UI with Next.js static export, served same-origin by FastAPI | Avoid a second hosting bill and CORS complexity |
| 2026-07-19 | Added GH Actions CI/CD + Render deploy hook, auto-deploy off | Production updates only after CI is green |
| Sprint 1 | Rebuilt eval harness to call real `rag_service.ask_document`, not the legacy shadow chain | Legacy harness skipped safety/confidence scoring — wasn't measuring what users see |
| Sprint 1 | Hybrid dense+BM25 retrieval over dense-only | Legal text needs exact-term matches (defined terms, section/dollar refs) alongside semantic similarity |
| Sprint 1 | Deterministic, non-LLM confidence scoring | Reproducible/auditable; a valid independent check against RAGAS's own LLM-judged scores |
| 2026-07-22 | Expanded dataset `v1`→`v2` (15→141 samples, 3→20 docs) | Broader coverage needed before scores are trustworthy rather than overfit to 3 contracts |
| Sprint 2A | `USE_LLM_CLASSIFIER` defaulted off, kept configurable | Keyword classifier matched LLM routing at zero cost; kept as fallback for future complexity |
| Sprint 2A | Added a query-embedding cache instead of restructuring retrieval | Embeddings are a pure function of (model, text) — caching can't change results, only removes a redundant round trip |
| 2026-07-22 (in progress) | Added Google Sign-In as a second identity method | Reduce signup friction; additive endpoints, no rewrite of existing JWT flow |
| Sprint 3 | Lowered RAGAS `RunConfig.max_workers` from the library default (16) to 4, added explicit retry/exception logging | Untuned 16-way concurrency against a client sized for one interactive request was the proximate cause of a run scoring only 5/141 valid Context Precision samples; logging then revealed the deeper cause was an OpenAI daily request-count bucket, not pure concurrency |
| Sprint 3 | Added a data-integrity gate (`_integrity_check`, 90% valid-sample threshold) to the benchmark report | `_mean()` correctly excludes missing scores from its denominator, but that same correctness let a near-total scoring failure produce a plausible-looking aggregate with no visible warning |
| Sprint 3 | Added checkpoint/resume to the benchmark harness, scored one sample per RAGAS call instead of one batched call for all samples | Multi-hour runs were being interrupted (session timeouts, host sleep, rate-limit exhaustion) and losing all progress; per-sample scoring is the only way to checkpoint between RAGAS calls, since a single batched `evaluate()` only returns at the end |
| Sprint 3 | Shipped `CHUNK_SIZE=256` (was 500), kept `CHUNK_OVERLAP=50` | Full chunk-size sweep (500/768/384/256) plus an overlap sweep at 256 (50 vs. 75) on the `v2` benchmark — 256/50 had the highest Faithfulness and Hard-question Faithfulness of every configuration tested, with Context Recall flat across the whole sweep |
| (design stage) | Stay a modular monolith, no microservices | Team/domain too small to justify a split; current layering already reflects future seams |

---

## Lessons Learned

- Never optimize before benchmarking — a change without a before/after number isn't done.
- An evaluation harness that doesn't exercise the real code path measures nothing useful.
- Preserve benchmark history — never let "current state" overwrite "how we got here."
- Segment quality metrics by difficulty/category before trusting an aggregate (hard/abstention
  questions score lower by design, not by regression).
- Prefer deterministic routing/scoring when an LLM call produces the same outcome for less.
- **A design document is not implemented code** — several thorough specs here describe a more
  mature target system than what's running; always verify against `backend/src/` before relying
  on one.
- Config flags that "won" an experiment should stay configurable, not deleted.

---

## Session Checklists

**Startup:** read this file in full → check [Current Project Status](#current-project-status) for
what's mid-flight → check [Roadmap](#roadmap) before proposing new work → check the latest
benchmark report (`evaluation/benchmark/results/reports/`) before any retrieval/prompt/model
change → treat root design docs as target-state references, verify specifics against actual code.

**Completion:** if a retrieval/chunking/prompt/model change was made, run the benchmark and record
the report → update [Current Project Status](#current-project-status) and [Roadmap](#roadmap) to
match what actually shipped → update [Known Technical Debt](#known-technical-debt) if debt was
closed or introduced → add a [Decision Log](#decision-log) row for any non-obvious decision → make
sure status/roadmap/decision-log don't contradict each other before finishing.

---

## Maintaining This File

Update it when: a sprint/task completes (move Next→Completed, add a Decision Log row if a real
choice was made); architecture changes (update the module map, repo structure, or tech stack
table); the benchmark dataset grows or a new run lands (update dataset facts and latest-metrics
table); deployment/CI config changes; the evaluation harness moves into CI or gets a real DB
schema; or a design-spec doc (`AUTH_ARCHITECTURE.md` etc.) moves from spec to merged code — in
that last case, update every section here that still describes the pre-implementation state.

Rule of thumb: if a future session reading only this file would come away with an inaccurate
picture of the repository, update it.
