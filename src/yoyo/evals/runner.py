from __future__ import annotations

import asyncio
import time
from pathlib import Path

from yoyo.evals.costs import estimate_cost
from yoyo.evals.judge import judge_result_async
from yoyo.evals.progress import write_progress
from yoyo.evals.providers import get_provider
from yoyo.evals.query_generator import generate_queries, load_query_templates
from yoyo.evals.reporting import summarize_results, write_judge_scores, write_results, write_scores
from yoyo.evals.scoring import run_hard_checks, score_results
from yoyo.evals.schemas import EvalResult, EvalSummary


async def _run_single_query(provider_impl, provider: str, model: str, query, per_query_timeout_seconds: float) -> EvalResult:
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

    return EvalResult(
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


# runner 是单模型评测的主流程文件。
# 它会完成：读题 -> 调模型 -> 保存结果 -> 自动打分 -> 汇总 summary。
async def run_evaluation(
    provider: str,
    model: str,
    template_path: str | Path,
    output_path: str | Path,
    score_output_path: str | Path | None = None,
    judge_score_output_path: str | Path | None = None,
    per_query_timeout_seconds: float = 90.0,
    query_concurrency: int = 3,
    progress_path: str | Path | None = None,
    judge_enabled: bool = False,
    judge_provider: str = "openrouter",
    judge_model: str = "openai/gpt-5.4-mini",
) -> tuple[list[EvalResult], EvalSummary]:
    template_data = load_query_templates(template_path)
    queries = generate_queries(template_data)
    provider_impl = get_provider(provider, model)
    semaphore = asyncio.Semaphore(query_concurrency)
    results: list[EvalResult] = []
    total_queries = len(queries)
    completed = 0

    async def guarded(query):
        nonlocal completed
        async with semaphore:
            result = await _run_single_query(provider_impl, provider, model, query, per_query_timeout_seconds)
            results.append(result)
            results.sort(key=lambda item: item.query_id)
            write_results(output_path, results)
            if score_output_path is not None:
                write_scores(score_output_path, score_results(results))
            completed += 1
            if progress_path is not None:
                write_progress(
                    progress_path,
                    {
                        "provider": provider,
                        "model": model,
                        "completed_queries": completed,
                        "total_queries": total_queries,
                        "percent": round((completed / total_queries) * 100, 2),
                    },
                )
            return result

    await asyncio.gather(*(guarded(query) for query in queries))

    scores = score_results(results)
    if score_output_path is not None:
        write_scores(score_output_path, scores)

    if judge_enabled and judge_score_output_path is not None:
        hard_checks = [run_hard_checks(result) for result in results]
        judge_scores = [
            await judge_result_async(
                result,
                hard_check,
                judge_provider=judge_provider,
                judge_model=judge_model,
            )
            for result, hard_check in zip(results, hard_checks)
        ]
        write_judge_scores(judge_score_output_path, judge_scores)

    summary = summarize_results(provider, model, results, scores)
    return results, summary


def run_evaluation_sync(
    provider: str,
    model: str,
    template_path: str | Path,
    output_path: str | Path,
    score_output_path: str | Path | None = None,
    judge_score_output_path: str | Path | None = None,
    per_query_timeout_seconds: float = 90.0,
    query_concurrency: int = 3,
    progress_path: str | Path | None = None,
    judge_enabled: bool = False,
    judge_provider: str = "openrouter",
    judge_model: str = "openai/gpt-5.4-mini",
) -> tuple[list[EvalResult], EvalSummary]:
    return asyncio.run(
        run_evaluation(
            provider,
            model,
            template_path,
            output_path,
            score_output_path,
            judge_score_output_path,
            per_query_timeout_seconds,
            query_concurrency,
            progress_path,
            judge_enabled,
            judge_provider,
            judge_model,
        )
    )
