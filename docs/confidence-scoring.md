# Confidence scoring

Every AI response includes a **measured** `confidence_score` (0–1) and
`confidence_level` (`High` | `Medium` | `Low`). Confidence is computed in
`backend/src/services/confidence.py` from retrieval and grounding signals —
it is **never** invented by the LLM.

## Factors

| Factor | Weight | Signal |
|--------|--------|--------|
| Retrieval score | 0.35 | Mean FAISS similarity `1 / (1 + L2 distance)`. Missing scores → 0. |
| Supporting chunks | 0.25 | `min(1, chunk_count / 3)`. |
| Citation coverage | 0.25 | Unique cited source indices ÷ available source indices. |
| Answer grounding | 0.15 | `[Source N]` density / structured evidence ratio / abstention heuristics. |

## Levels

| Level | Score | Behavior |
|-------|-------|----------|
| High | ≥ 0.72 | Return answer normally. |
| Medium | ≥ 0.45 | Return answer + recommend optional expert review. |
| Low | < 0.45 | Do not answer confidently; recommend consulting a legal professional. |

## Applies to

`/ask`, `/ask/stream`, `/compare`, `/explain`, `/risks`.
