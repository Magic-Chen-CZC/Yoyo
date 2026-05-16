from __future__ import annotations

import argparse
from pathlib import Path

from yoyo.evals.translation_runner import run_translation_benchmark_sync


def main() -> None:
    parser = argparse.ArgumentParser(description="Run translation benchmark")
    parser.add_argument("--suite", required=True, choices=["product_translation", "routing_preprocess"])
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--disable-bilingual", action="store_true")
    args = parser.parse_args()

    _, summary = run_translation_benchmark_sync(
        suite=args.suite,
        dataset_path=Path(args.dataset),
        provider=args.provider,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        output_path=Path(args.output),
        summary_output_path=Path(args.summary_output),
        bilingual_enabled=not args.disable_bilingual,
    )
    print(summary)


if __name__ == "__main__":
    main()
