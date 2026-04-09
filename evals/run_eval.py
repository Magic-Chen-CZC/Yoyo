from __future__ import annotations

import argparse
from pathlib import Path

from yoyo.evals.runner import run_evaluation_sync


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Yoyo model evaluation")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--dataset",
        default="evals/datasets/query_templates.yaml",
    )
    parser.add_argument(
        "--output",
        default="evals/results/latest_results.json",
    )
    args = parser.parse_args()

    _, summary = run_evaluation_sync(
        provider=args.provider,
        model=args.model,
        template_path=Path(args.dataset),
        output_path=Path(args.output),
    )
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
