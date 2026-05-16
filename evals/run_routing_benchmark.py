from __future__ import annotations

import argparse
from pathlib import Path

from yoyo.evals.routing import run_routing_benchmark_sync, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run routing benchmark against router-only pipeline")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--output-cases", required=True)
    parser.add_argument("--output-summary", required=True)
    parser.add_argument("--fallback-enabled", action="store_true")
    parser.add_argument("--fallback-provider")
    parser.add_argument("--fallback-model")
    args = parser.parse_args()

    cases, summary = run_routing_benchmark_sync(
        Path(args.dataset),
        candidate_name=args.candidate_name,
        fallback_enabled=args.fallback_enabled,
        fallback_provider=args.fallback_provider,
        fallback_model=args.fallback_model,
    )
    write_json(args.output_cases, cases)
    write_json(args.output_summary, summary)


if __name__ == "__main__":
    main()
