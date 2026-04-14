from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook



def load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))



def export_results_to_excel(results_dir: Path, output_path: Path) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)

    summary_sheet = workbook.create_sheet("summaries")
    summary_headers = [
        "provider",
        "model",
        "total_queries",
        "avg_latency_ms",
        "estimated_total_input_cost",
        "estimated_total_output_cost",
        "estimated_total_cost",
        "avg_prompt_tokens",
        "avg_completion_tokens",
        "avg_total_tokens",
        "avg_score",
    ]
    summary_sheet.append(summary_headers)

    result_sheet = workbook.create_sheet("results")
    result_headers = [
        "query_id",
        "provider",
        "model",
        "prompt",
        "response_text",
        "latency_ms",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "estimated_input_cost",
        "estimated_output_cost",
        "total_cost",
        "parameter_size",
        "category",
        "language",
        "title",
        "mode",
        "expected_intent",
        "expected_data_source",
    ]
    result_sheet.append(result_headers)

    score_sheet = workbook.create_sheet("scores")
    score_headers = ["query_id", "provider", "model", "category", "score", "max_score", "rationale"]
    score_sheet.append(score_headers)

    judge_sheet = workbook.create_sheet("judge_scores")
    judge_headers = [
        "query_id",
        "provider",
        "model",
        "category",
        "judge_provider",
        "judge_model",
        "judge_version",
        "rubric_version",
        "overall_score",
        "decision",
        "confidence",
        "judge_latency_ms",
        "judge_total_tokens",
        "judge_total_cost",
    ]
    judge_sheet.append(judge_headers)

    for summary_file in sorted(results_dir.glob("*_summary.json")):
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        summary_sheet.append([summary.get(header) for header in summary_headers])

    for result_file in sorted(results_dir.glob("*_results.json")):
        for item in load_json(result_file):
            metadata = item.get("metadata", {})
            result_sheet.append(
                [
                    item.get("query_id"),
                    item.get("provider"),
                    item.get("model"),
                    item.get("prompt"),
                    item.get("response_text"),
                    item.get("latency_ms"),
                    item.get("prompt_tokens"),
                    item.get("completion_tokens"),
                    item.get("total_tokens"),
                    item.get("estimated_input_cost"),
                    item.get("estimated_output_cost"),
                    item.get("total_cost"),
                    item.get("parameter_size"),
                    metadata.get("category"),
                    metadata.get("language"),
                    metadata.get("title"),
                    metadata.get("mode"),
                    metadata.get("expected_intent"),
                    metadata.get("expected_data_source"),
                ]
            )

    for score_file in sorted(results_dir.glob("*_scores.json")):
        for item in load_json(score_file):
            score_sheet.append([item.get(header) for header in score_headers])

    for judge_file in sorted(results_dir.glob("*_judge_scores.json")):
        for item in load_json(judge_file):
            judge_sheet.append([item.get(header) for header in judge_headers])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    export_results_to_excel(project_root / "evals" / "results", project_root / "benchmark_results.xlsx")
