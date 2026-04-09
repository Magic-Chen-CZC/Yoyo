from __future__ import annotations

import json
from pathlib import Path

from yoyo.evals.batch import load_model_matrix
from yoyo.evals.runner import run_evaluation_sync


def run_and_write_summaries(model_matrix_path: Path, dataset_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in load_model_matrix(model_matrix_path):
        provider = item["provider"]
        model = item["model"]
        safe_name = f"{provider}_{model}".replace("/", "_")
        results_path = output_dir / f"{safe_name}_results.json"
        scores_path = output_dir / f"{safe_name}_scores.json"
        _, summary = run_evaluation_sync(
            provider=provider,
            model=model,
            template_path=dataset_path,
            output_path=results_path,
            score_output_path=scores_path,
        )
        (output_dir / f"{safe_name}_summary.json").write_text(
            summary.model_dump_json(indent=2),
            encoding="utf-8",
        )
