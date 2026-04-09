from __future__ import annotations

import asyncio
import time
from pathlib import Path

from yoyo.evals.costs import estimate_cost
from yoyo.evals.providers import get_provider
from yoyo.evals.query_generator import generate_queries, load_query_templates
from yoyo.evals.reporting import summarize_results, write_results, write_scores
from yoyo.evals.scoring import score_results
from yoyo.evals.schemas import EvalResult, EvalSummary


async def run_evaluation(
    provider: str,
    model: str,
    template_path: str | Path,
    output_path: str | Path,
    score_output_path: str | Path | None = None,
    per_query_timeout_seconds: float = 90.0,
) -> tuple[list[EvalResult], EvalSummary]:
    template_data = load_query_templates(template_path)
    queries = generate_queries(template_data)
    provider_impl = get_provider(provider, model)

    results: list[EvalResult] = []
    for query in queries:
        started = time.perf_counter()
        generation = await asyncio.wait_for(
            provider_impl.generate(query.prompt),
            timeout=per_query_timeout_seconds,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        response_text = str(generation["text"])
        usage = generation.get("usage") or {}

        input_cost, output_cost, parameter_size = estimate_cost(provider, model, query.prompt, response_text)
        total_cost = usage.get("cost")
        if total_cost is None and input_cost is not None and output_cost is not None:
            total_cost = input_cost + output_cost

        results.append(
            EvalResult(
                query_id=query.id,
                provider=provider,
                model=model,
                prompt=query.prompt,
                response_text=response_text,
                latency_ms=latency_ms,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                estimated_input_cost=input_cost,
                estimated_output_cost=output_cost,
                total_cost=total_cost,
                parameter_size=parameter_size,
                metadata={
                    "category": query.category,
                    "language": query.language,
                    **query.metadata,
                },
            )
        )

    write_results(output_path, results)
    scores = score_results(results)
    if score_output_path is not None:
        write_scores(score_output_path, scores)
    summary = summarize_results(provider, model, results, scores)
    return results, summary


def run_evaluation_sync(
    provider: str,
    model: str,
    template_path: str | Path,
    output_path: str | Path,
    score_output_path: str | Path | None = None,
    per_query_timeout_seconds: float = 90.0,
) -> tuple[list[EvalResult], EvalSummary]:
    return asyncio.run(
        run_evaluation(
            provider,
            model,
            template_path,
            output_path,
            score_output_path,
            per_query_timeout_seconds,
        )
    )
