"""Benchmark evaluation harness — runs the real production RAG pipeline against a
versioned benchmark dataset and scores it with RAGAS.

Import order matters: `environment` must be the first module imported from this
package (before any other `src.*` import happens in the calling process), since it
isolates the run's database/upload/index/log paths from production data. `cli.py`
does this correctly; if you add a new entrypoint, follow the same pattern.
"""
