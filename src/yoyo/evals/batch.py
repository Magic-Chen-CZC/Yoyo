from __future__ import annotations

import json
from pathlib import Path

import yaml

from yoyo.evals.runner import run_evaluation_sync
from yoyo.evals.schemas import EvalSummary


def load_model_matrix(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return list(data.get("models", []))


def run_batch_evaluation(
    model_matrix_path: str | Path,
    dataset_path: str | Path,
    output_dir: str | Path,
) -> list[EvalSummary]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    summaries: list[EvalSummary] = []
    for item in load_model_matrix(model_matrix_path):
        provider = item["provider"]
        model = item["model"]
        safe_name = f"{provider}_{model}".replace("/", "_")
        results_path = output_root / f"{safe_name}_results.json"
        scores_path = output_root / f"{safe_name}_scores.json"
        summary_path = output_root / f"{safe_name}_summary.json"
        error_path = output_root / f"{safe_name}_error.json"
        try:
            _, summary = run_evaluation_sync(
                provider=provider,
                model=model,
                template_path=dataset_path,
                output_path=results_path,
                score_output_path=scores_path,
                per_query_timeout_seconds=90.0,
            )
            summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
            summaries.append(summary)
        except Exception as error:
            error_path.write_text(
                json.dumps({"provider": provider, "model": model, "error": str(error)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    return summaries
