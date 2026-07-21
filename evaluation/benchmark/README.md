# RAG Evaluation Benchmark — Data

This directory holds the **versioned benchmark dataset and evaluation run history** for the RAG
Evaluation Framework. Full design rationale lives in `/RAG_EVALUATION_ARCHITECTURE.md` at the repo
root — this file is a short pointer for anyone adding samples or reading results, not a
replacement for that document.

The harness code that runs this dataset lives in `backend/src/evaluation/benchmark/` (a Python
package), not here — this directory is data only.

## Layout

```
evaluation/benchmark/
├── datasets/
│   └── v1/
│       ├── manifest.json      # dataset version metadata
│       ├── documents/         # synthetic fixture documents (never real user data)
│       └── samples/
│           └── contract/      # one JSON file per benchmark question
├── results/
│   ├── runs/                  # one JSON file per evaluation run (raw + aggregate scores)
│   └── reports/                # one markdown report per run
└── .state/                    # gitignored — isolated runtime DB/uploads/indexes/logs for eval runs
```

## Adding a benchmark sample

1. Add the fixture document under `datasets/<version>/documents/` if it doesn't already exist
   (synthetic or public-domain text only — never a real user's uploaded document).
2. Add a sample JSON file under `datasets/<version>/samples/<category>/` following the existing
   files' schema (`id`, `question`, `ground_truth_answer`, `source_document`,
   `expected_citations`, `document_metadata`, `difficulty`, `category`, `question_type`, `tags`,
   `dataset_version`).
3. Have the ground truth answer reviewed against the source document before merging — a wrong
   ground truth silently corrupts every RAGAS score computed against it.
4. Never edit or delete a sample that a past run has already referenced (`results/runs/*.json`
   records exactly which samples it used) — supersede it with a new sample id instead, so
   historical comparisons stay valid.

## Running the benchmark

See `RAG_EVALUATION_ARCHITECTURE.md` Section 5, or run:

```bash
PYTHONPATH=backend python backend/scripts/run_benchmark.py
```
