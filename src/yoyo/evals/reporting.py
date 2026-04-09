from __future__ import annotations

import json
from pathlib import Path

from yoyo.evals.schemas import EvalResult, EvalScore, EvalSummary


def write_results(path: str | Path, results: list[EvalResult]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([result.model_dump() for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_scores(path: str | Path, scores: list[EvalScore]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([score.model_dump() for score in scores], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def summarize_results(
    provider: str,
    model: str,
    results: list[EvalResult],
    scores: list[EvalScore],
) -> EvalSummary:
    total_queries = len(results)
    avg_latency_ms = sum(result.latency_ms for result in results) / total_queries if total_queries else 0.0
    total_input_cost = sum(result.estimated_input_cost or 0.0 for result in results)
    total_output_cost = sum(result.estimated_output_cost or 0.0 for result in results)
    total_cost = sum(result.total_cost or 0.0 for result in results)
    avg_prompt_tokens = sum(result.prompt_tokens or 0 for result in results) / total_queries if total_queries else 0.0
    avg_completion_tokens = sum(result.completion_tokens or 0 for result in results) / total_queries if total_queries else 0.0
    avg_total_tokens = sum(result.total_tokens or 0 for result in results) / total_queries if total_queries else 0.0
    avg_score = sum(score.score for score in scores) / len(scores) if scores else 0.0
    return EvalSummary(
        provider=provider,
        model=model,
        total_queries=total_queries,
        avg_latency_ms=avg_latency_ms,
        estimated_total_input_cost=total_input_cost,
        estimated_total_output_cost=total_output_cost,
        estimated_total_cost=total_cost,
        avg_prompt_tokens=avg_prompt_tokens,
        avg_completion_tokens=avg_completion_tokens,
        avg_total_tokens=avg_total_tokens,
        avg_score=avg_score,
    )
