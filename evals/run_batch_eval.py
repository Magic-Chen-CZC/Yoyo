from __future__ import annotations

import argparse
from pathlib import Path

from yoyo.evals.batch import run_batch_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Yoyo batch model evaluation")
    parser.add_argument("--models", default="evals/models.yaml")
    parser.add_argument("--dataset", default="evals/datasets/query_templates.yaml")
    parser.add_argument("--output-dir", default="evals/results")
    args = parser.parse_args()

    summaries = run_batch_evaluation(
        model_matrix_path=Path(args.models),
        dataset_path=Path(args.dataset),
        output_dir=Path(args.output_dir),
    )

    for summary in summaries:
        print(summary.model_dump_json(indent=2))
    if not summaries:
        print("No model run completed successfully.")


if __name__ == "__main__":
    main()
