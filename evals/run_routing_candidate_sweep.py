from __future__ import annotations

import argparse
from pathlib import Path

from yoyo.evals.routing import load_routing_candidates, run_routing_benchmark_sync, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run routing candidate sweep")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []

    for candidate in load_routing_candidates(args.candidates):
        candidate_name = str(candidate["name"])
        safe_name = candidate_name.replace("/", "_")
        cases, summary = run_routing_benchmark_sync(
            dataset_path,
            candidate_name=candidate_name,
            fallback_enabled=bool(candidate.get("fallback_enabled", False)),
            fallback_provider=candidate.get("fallback_provider"),
            fallback_model=candidate.get("fallback_model"),
        )
        write_json(output_dir / f"{safe_name}_cases.json", cases)
        write_json(output_dir / f"{safe_name}_summary.json", summary)
        summaries.append(summary)

    write_json(output_dir / "routing_sweep_summary.json", summaries)


if __name__ == "__main__":
    main()
