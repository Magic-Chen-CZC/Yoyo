from __future__ import annotations

# batch.py 负责一次性跑多个模型。
# 你可以把它理解成“多模型联赛总控器”：逐个跑模型，然后再统一生成比较结果。
import asyncio
import json
from pathlib import Path

import yaml

from yoyo.evals.progress import write_progress
from yoyo.evals.providers import MissingEvalAPIKeyError
from yoyo.evals.reporting import (
    build_category_breakdown,
    build_comparative_markdown,
    build_ranking_rows,
    load_scores,
    model_key,
    write_comparative_report,
    write_summary,
)
from yoyo.evals.runner import run_evaluation
from yoyo.evals.schemas import EvalSummary


def load_model_matrix(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return list(data.get("models", []))


async def _run_model(item: dict[str, str], dataset_path: Path, output_root: Path) -> EvalSummary | None:
    provider = item["provider"]
    model = item["model"]
    safe_name = f"{provider}_{model}".replace("/", "_")
    results_path = output_root / f"{safe_name}_results.json"
    scores_path = output_root / f"{safe_name}_scores.json"
    summary_path = output_root / f"{safe_name}_summary.json"
    error_path = output_root / f"{safe_name}_error.json"
    progress_path = output_root / f"{safe_name}_progress.json"
    try:
        _, summary = await run_evaluation(
            provider=provider,
            model=model,
            template_path=dataset_path,
            output_path=results_path,
            score_output_path=scores_path,
            per_query_timeout_seconds=90.0,
            query_concurrency=3,
            progress_path=progress_path,
        )
        write_summary(summary_path, summary)
        return summary
    except MissingEvalAPIKeyError as error:
        error_path.write_text(
            json.dumps(
                {
                    "provider": provider,
                    "model": model,
                    "error": str(error),
                    "status": "invalid",
                    "reason": "missing_api_key",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return None
    except Exception as error:
        error_path.write_text(
            json.dumps(
                {
                    "provider": provider,
                    "model": model,
                    "error": str(error),
                    "status": "error",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return None


def _write_batch_report(output_root: Path, summaries: list[EvalSummary]) -> None:
    if not summaries:
        return

    scores_by_model = {}
    for summary in summaries:
        safe_name = f"{summary.provider}_{summary.model}".replace("/", "_")
        scores_path = output_root / f"{safe_name}_scores.json"
        scores_by_model[model_key(summary.provider, summary.model)] = load_scores(scores_path)

    category_breakdown = build_category_breakdown(scores_by_model)
    ranking_rows = build_ranking_rows(summaries)
    markdown = build_comparative_markdown(summaries, category_breakdown)
    write_comparative_report(output_root / "batch_comparison.md", markdown)
    (output_root / "batch_ranking.json").write_text(
        json.dumps({"rankings": ranking_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_root / "batch_category_breakdown.json").write_text(
        json.dumps(category_breakdown, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_batch_evaluation(
    model_matrix_path: str | Path,
    dataset_path: str | Path,
    output_dir: str | Path,
) -> list[EvalSummary]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    model_matrix = load_model_matrix(model_matrix_path)

    async def main() -> list[EvalSummary]:
        total_models = len(model_matrix)
        write_progress(
            output_root / "batch_progress.json",
            {
                "total_models": total_models,
                "started_models": total_models,
                "message": "Batch benchmark started",
            },
        )
        results = await asyncio.gather(
            *[_run_model(item, Path(dataset_path), output_root) for item in model_matrix]
        )
        summaries = [summary for summary in results if summary is not None]
        _write_batch_report(output_root, summaries)
        write_progress(
            output_root / "batch_progress.json",
            {
                "total_models": total_models,
                "completed_models": len(summaries),
                "message": "Batch benchmark finished",
            },
        )
        return summaries

    return asyncio.run(main())
