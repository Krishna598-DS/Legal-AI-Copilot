"""Benchmark dataset loading.

Samples are versioned JSON files checked into git under
``evaluation/benchmark/datasets/<version>/samples/**/*.json`` (see the architecture
spec, ``RAG_EVALUATION_ARCHITECTURE.md`` Section 2, for the schema rationale). This
module only reads that data — it has no dependency on the rest of the application,
so it can be imported and tested without touching settings/database/RAG code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkSample:
    id: str
    question: str
    ground_truth_answer: str
    source_document_id: str
    category: str
    difficulty: str
    question_type: str
    dataset_version: str
    expected_citations: list[dict] = field(default_factory=list)
    document_metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: Path) -> "BenchmarkSample":
        data = json.loads(path.read_text(encoding="utf-8"))
        source_document = data["source_document"]
        return cls(
            id=data["id"],
            question=data["question"],
            ground_truth_answer=data["ground_truth_answer"],
            source_document_id=source_document["document_id"],
            category=data.get("category", source_document.get("category", "uncategorized")),
            difficulty=data.get("difficulty", "medium"),
            question_type=data.get("question_type", "general"),
            dataset_version=data.get("dataset_version", "v1"),
            expected_citations=data.get("expected_citations", []),
            document_metadata=data.get("document_metadata", {}),
            tags=data.get("tags", []),
        )


@dataclass(frozen=True)
class BenchmarkDataset:
    version: str
    documents_dir: Path
    samples: list[BenchmarkSample]


def load_dataset(dataset_dir: Path) -> BenchmarkDataset:
    """Load one dataset version directory: manifest + documents/ + samples/**/*.json."""
    dataset_dir = Path(dataset_dir)
    manifest_path = dataset_dir / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {}
    )
    version = manifest.get("dataset_version", dataset_dir.name)

    samples_dir = dataset_dir / "samples"
    sample_files = sorted(samples_dir.rglob("*.json"))
    samples = [BenchmarkSample.from_json(p) for p in sample_files]
    if not samples:
        raise ValueError(f"No benchmark samples found under {samples_dir}")

    documents_dir = dataset_dir / "documents"
    return BenchmarkDataset(version=version, documents_dir=documents_dir, samples=samples)
