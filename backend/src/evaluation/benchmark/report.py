"""Console + markdown report rendering for a single benchmark run."""

from __future__ import annotations

METRIC_LABELS = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "Answer Relevancy",
    "context_precision": "Context Precision",
    "context_recall": "Context Recall",
}


def _fmt(value) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) else "n/a"


def _delta_str(current, previous) -> str:
    if not isinstance(current, (int, float)) or not isinstance(previous, (int, float)):
        return ""
    delta = current - previous
    sign = "+" if delta >= 0 else ""
    return f" ({sign}{delta:.4f} vs previous)"


def render_console_summary(run_record: dict, previous_run: dict | None) -> str:
    overall = run_record["aggregate_scores"]["overall"]
    prev_overall = (previous_run or {}).get("aggregate_scores", {}).get("overall", {})
    integrity = run_record["aggregate_scores"].get("data_integrity")

    lines = [
        "=" * 64,
        "RAG BENCHMARK EVALUATION REPORT",
        "=" * 64,
        f"Run:        {run_record['run_id']}",
        f"Dataset:    {run_record['dataset_version']}",
        f"Git commit: {run_record.get('git_commit') or 'n/a'}",
        f"Samples:    {overall['sample_count']}  (errors: {overall['error_count']})",
    ]
    if integrity and not integrity["valid"]:
        lines += [
            "!" * 64,
            "BENCHMARK INTEGRITY: INVALID — scores below are not reliable",
            *[f"  - {issue}" for issue in integrity["issues"]],
            "!" * 64,
        ]
    lines += [
        "-" * 64,
        "RAGAS SCORES",
    ]
    for key, label in METRIC_LABELS.items():
        value = overall.get(key)
        lines.append(f"  {label:<20} {_fmt(value)}{_delta_str(value, prev_overall.get(key))}")

    lines += [
        "-" * 64,
        "PERFORMANCE",
        f"  Retrieval latency (mean)    {overall.get('retrieval_latency_ms')} ms",
        f"  Generation latency (mean)   {overall.get('generation_latency_ms')} ms",
        f"  End-to-end latency (mean)   {overall.get('end_to_end_latency_s')} s",
        f"  Embedding latency (mean)    {overall.get('embedding_latency_ms')} ms "
        f"({overall.get('embedding_call_count')} calls/question, "
        f"{overall.get('embedding_cache_hits')} cache hits, "
        f"{overall.get('embedding_cache_misses')} cache misses)",
        f"  Product confidence (mean)   {overall.get('confidence_score')}",
        "-" * 64,
        "TOKENS & COST (mean per question)",
        f"  Estimated embedding tokens  {overall.get('estimated_embedding_tokens')}",
        f"  Prompt tokens               {overall.get('prompt_tokens')}",
        f"  Completion tokens           {overall.get('completion_tokens')}",
        f"  Total tokens                {overall.get('total_tokens')}",
        f"  Estimated cost (USD)        {overall.get('total_cost_usd')}",
        "-" * 64,
        "BY CATEGORY",
    ]
    for name, summary in run_record["aggregate_scores"]["by_category"].items():
        lines.append(
            f"  {name}: faithfulness={_fmt(summary.get('faithfulness'))} "
            f"relevancy={_fmt(summary.get('answer_relevancy'))} "
            f"precision={_fmt(summary.get('context_precision'))} "
            f"recall={_fmt(summary.get('context_recall'))} (n={summary.get('sample_count')})"
        )

    lines.append("BY DIFFICULTY")
    for name, summary in run_record["aggregate_scores"]["by_difficulty"].items():
        lines.append(
            f"  {name}: faithfulness={_fmt(summary.get('faithfulness'))} "
            f"relevancy={_fmt(summary.get('answer_relevancy'))} "
            f"precision={_fmt(summary.get('context_precision'))} "
            f"recall={_fmt(summary.get('context_recall'))} (n={summary.get('sample_count')})"
        )
    lines.append("=" * 64)
    return "\n".join(lines)


def render_markdown_report(run_record: dict, previous_run: dict | None) -> str:
    overall = run_record["aggregate_scores"]["overall"]
    prev_overall = (previous_run or {}).get("aggregate_scores", {}).get("overall", {})
    integrity = run_record["aggregate_scores"].get("data_integrity")

    lines = [
        f"# RAG Benchmark Report — {run_record['run_id']}",
        "",
        f"- Dataset version: `{run_record['dataset_version']}`",
        f"- Git commit: `{run_record.get('git_commit') or 'n/a'}`",
        f"- Model: `{run_record['model_config']['llm_model']}` / "
        f"`{run_record['model_config']['embedding_model']}`",
        f"- Retrieval: k={run_record['model_config']['retrieval_k']}, "
        f"chunk_size={run_record['model_config']['chunk_size']}, "
        f"chunk_overlap={run_record['model_config']['chunk_overlap']}, "
        f"hybrid_weights=({run_record['model_config']['hybrid_dense_weight']}, "
        f"{run_record['model_config']['hybrid_bm25_weight']})",
        f"- Samples evaluated: {overall['sample_count']} (errors: {overall['error_count']})",
        f"- Previous run compared: `{previous_run['run_id'] if previous_run else 'none'}`",
        "",
    ]
    if integrity and not integrity["valid"]:
        lines += [
            "## ⚠️ BENCHMARK INTEGRITY: INVALID",
            "",
            "The scores in this report are **not reliable** — too few samples scored "
            "successfully for one or more metrics:",
            "",
            *[f"- {issue}" for issue in integrity["issues"]],
            "",
        ]
    lines += [
        "## RAGAS scores",
        "",
        "| Metric | Score | vs previous |",
        "|---|---|---|",
    ]
    for key, label in METRIC_LABELS.items():
        value = overall.get(key)
        delta = _delta_str(value, prev_overall.get(key)).replace(" vs previous", "").strip()
        lines.append(f"| {label} | {_fmt(value)} | {delta or '—'} |")

    lines += [
        "",
        "## Performance",
        "",
        f"- Mean retrieval latency: {overall.get('retrieval_latency_ms')} ms",
        f"- Mean generation latency: {overall.get('generation_latency_ms')} ms",
        f"- Mean end-to-end latency: {overall.get('end_to_end_latency_s')} s",
        f"- Mean embedding latency: {overall.get('embedding_latency_ms')} ms "
        f"({overall.get('embedding_call_count')} embedding calls/question, "
        f"{overall.get('embedding_cache_hits')} cache hits, "
        f"{overall.get('embedding_cache_misses')} cache misses)",
        f"- Mean product confidence score: {overall.get('confidence_score')}",
        "",
        "## Tokens & cost (mean per question)",
        "",
        f"- Estimated embedding tokens: {overall.get('estimated_embedding_tokens')}",
        f"- Prompt tokens: {overall.get('prompt_tokens')}",
        f"- Completion tokens: {overall.get('completion_tokens')}",
        f"- Total tokens: {overall.get('total_tokens')}",
        f"- Estimated cost per request (USD): {overall.get('total_cost_usd')}",
        "",
        "## Scores by category",
        "",
        "| Category | Faithfulness | Relevancy | Precision | Recall | N |",
        "|---|---|---|---|---|---|",
    ]
    for name, summary in run_record["aggregate_scores"]["by_category"].items():
        lines.append(
            f"| {name} | {_fmt(summary.get('faithfulness'))} "
            f"| {_fmt(summary.get('answer_relevancy'))} "
            f"| {_fmt(summary.get('context_precision'))} "
            f"| {_fmt(summary.get('context_recall'))} | {summary.get('sample_count')} |"
        )

    lines += [
        "",
        "## Scores by difficulty",
        "",
        "| Difficulty | Faithfulness | Relevancy | Precision | Recall | N |",
        "|---|---|---|---|---|---|",
    ]
    for name, summary in run_record["aggregate_scores"]["by_difficulty"].items():
        lines.append(
            f"| {name} | {_fmt(summary.get('faithfulness'))} "
            f"| {_fmt(summary.get('answer_relevancy'))} "
            f"| {_fmt(summary.get('context_precision'))} "
            f"| {_fmt(summary.get('context_recall'))} | {summary.get('sample_count')} |"
        )

    lines += [
        "",
        "## Per-question results",
        "",
        "| ID | Category | Difficulty | Faithfulness | Relevancy | Precision | Recall | Confidence | Error |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in run_record["results"]:
        lines.append(
            f"| {r['sample_id']} | {r['category']} | {r['difficulty']} "
            f"| {_fmt(r.get('faithfulness'))} | {_fmt(r.get('answer_relevancy'))} "
            f"| {_fmt(r.get('context_precision'))} | {_fmt(r.get('context_recall'))} "
            f"| {r.get('confidence_level') or 'n/a'} | {r.get('error') or ''} |"
        )

    return "\n".join(lines) + "\n"
