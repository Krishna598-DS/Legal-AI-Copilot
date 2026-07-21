"""
CLI entrypoint: run the benchmark dataset through the production RAG pipeline and
print + save a RAGAS evaluation report.

Usage (from repo root, with OPENAI_API_KEY configured in .env):

    PYTHONPATH=backend python backend/scripts/run_benchmark.py
    PYTHONPATH=backend python backend/scripts/run_benchmark.py --dataset-dir evaluation/benchmark/datasets/v1
"""

from __future__ import annotations

import argparse
import asyncio

# Must be the first `src.*`-touching import in this process — isolates the benchmark
# run from production data (separate SQLite DB, separate upload/index/log directories).
from src.evaluation.benchmark import environment  # noqa: F401  (import order matters)

from src.evaluation.benchmark.dataset import load_dataset
from src.evaluation.benchmark.ragas_eval import run_ragas
from src.evaluation.benchmark.report import render_console_summary, render_markdown_report
from src.evaluation.benchmark.runner import run_benchmark
from src.evaluation.benchmark.storage import build_run_record, find_previous_run, persist_run

_DEFAULT_DATASET_DIR = environment.BENCHMARK_DIR / "datasets" / "v1"
_REPORTS_DIR = environment.BENCHMARK_DIR / "results" / "reports"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RAG evaluation benchmark.")
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default=str(_DEFAULT_DATASET_DIR),
        help="Benchmark dataset version directory (default: datasets/v1).",
    )
    args = parser.parse_args()

    dataset = load_dataset(args.dataset_dir)
    print(f"Loaded {len(dataset.samples)} benchmark samples (dataset {dataset.version}).")
    print("Ingesting fixture documents and running each question through the production "
          "RAG pipeline (retrieval + generation + safety scrubbing + confidence scoring)...")

    results = asyncio.run(run_benchmark(dataset))

    error_count = sum(1 for r in results if r.error)
    if error_count:
        print(f"WARNING: {error_count}/{len(results)} samples errored — see the report for detail.")

    print("Running RAGAS (faithfulness, answer relevancy, context precision, context recall)...")
    scored = run_ragas(results)

    run_record = build_run_record(dataset.version, scored)
    previous_run = find_previous_run(dataset.version, run_record["run_id"])

    saved_path = persist_run(run_record)

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _REPORTS_DIR / f"{run_record['run_id']}.md"
    report_path.write_text(render_markdown_report(run_record, previous_run), encoding="utf-8")

    print()
    print(render_console_summary(run_record, previous_run))
    print(f"\nSaved raw results to {saved_path}")
    print(f"Saved markdown report to {report_path}")


if __name__ == "__main__":
    main()
