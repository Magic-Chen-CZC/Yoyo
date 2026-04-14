from __future__ import annotations

import json
from pathlib import Path

from yoyo.evals.schemas import EvalResult, EvalScore, EvalSummary, JudgeResult



def _write_json(path: str | Path, payload: object) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")



def write_results(path: str | Path, results: list[EvalResult]) -> None:
    _write_json(path, [result.model_dump() for result in results])



def write_scores(path: str | Path, scores: list[EvalScore]) -> None:
    _write_json(path, [score.model_dump() for score in scores])



def write_judge_scores(path: str | Path, judge_scores: list[JudgeResult]) -> None:
    _write_json(path, [judge.model_dump() for judge in judge_scores])



def write_summary(path: str | Path, summary: EvalSummary) -> None:
    _write_json(path, summary.model_dump())



def load_scores(path: str | Path) -> list[EvalScore]:
    input_path = Path(path)
    if not input_path.exists():
        return []
    data = json.loads(input_path.read_text(encoding="utf-8"))
    return [EvalScore.model_validate(item) for item in data]



def load_judge_scores(path: str | Path) -> list[JudgeResult]:
    input_path = Path(path)
    if not input_path.exists():
        return []
    data = json.loads(input_path.read_text(encoding="utf-8"))
    return [JudgeResult.model_validate(item) for item in data]


# reporting.py 负责把原始评测结果整理成“人能看”的汇总信息。
def summarize_results(
    provider: str,
    model: str,
    results: list[EvalResult],
    scores: list[EvalScore],
) -> EvalSummary:
    total_queries = len(results)
    avg_latency_ms = sum(result.latency_ms for result in results) / total_queries if total_queries else 0.0
    total_input_cost = sum(result.estimated_input_cost or 0.0 for result in results)
    total_output_cost = sum(result.estimated_output_cost or 0.0 for result in results)
    total_cost = sum(result.total_cost or 0.0 for result in results)
    avg_prompt_tokens = sum(result.prompt_tokens or 0 for result in results) / total_queries if total_queries else 0.0
    avg_completion_tokens = sum(result.completion_tokens or 0 for result in results) / total_queries if total_queries else 0.0
    avg_total_tokens = sum(result.total_tokens or 0 for result in results) / total_queries if total_queries else 0.0
    avg_score = sum(score.score for score in scores) / len(scores) if scores else 0.0
    return EvalSummary(
        provider=provider,
        model=model,
        total_queries=total_queries,
        avg_latency_ms=avg_latency_ms,
        estimated_total_input_cost=total_input_cost,
        estimated_total_output_cost=total_output_cost,
        estimated_total_cost=total_cost,
        avg_prompt_tokens=avg_prompt_tokens,
        avg_completion_tokens=avg_completion_tokens,
        avg_total_tokens=avg_total_tokens,
        avg_score=avg_score,
    )



def model_key(provider: str, model: str) -> str:
    return f"{provider}:{model}"



def rank_summaries(summaries: list[EvalSummary]) -> list[EvalSummary]:
    return sorted(
        summaries,
        key=lambda summary: (
            -summary.avg_score,
            summary.avg_latency_ms,
            summary.estimated_total_cost,
            summary.provider,
            summary.model,
        ),
    )



def build_ranking_rows(summaries: list[EvalSummary]) -> list[dict[str, object]]:
    ranked = rank_summaries(summaries)
    return [
        {
            "rank": index,
            "provider": summary.provider,
            "model": summary.model,
            "avg_score": round(summary.avg_score, 2),
            "avg_latency_ms": round(summary.avg_latency_ms, 2),
            "estimated_total_cost": round(summary.estimated_total_cost, 6),
            "total_queries": summary.total_queries,
        }
        for index, summary in enumerate(ranked, start=1)
    ]



def build_category_breakdown(scores_by_model: dict[str, list[EvalScore]]) -> dict[str, dict[str, float]]:
    categories = sorted({score.category for scores in scores_by_model.values() for score in scores if score.category})
    breakdown: dict[str, dict[str, float]] = {}
    for category in categories:
        category_rows: dict[str, float] = {}
        for key in sorted(scores_by_model):
            category_scores = [score.score for score in scores_by_model[key] if score.category == category]
            if category_scores:
                category_rows[key] = round(sum(category_scores) / len(category_scores), 2)
        breakdown[category] = category_rows
    return breakdown



def build_language_breakdown(results_by_model: dict[str, list[EvalResult]]) -> dict[str, dict[str, float]]:
    languages = sorted({str(result.metadata.get("language")) for results in results_by_model.values() for result in results})
    breakdown: dict[str, dict[str, float]] = {}
    for language in languages:
        rows: dict[str, float] = {}
        for key, results in sorted(results_by_model.items()):
            language_results = [result for result in results if str(result.metadata.get("language")) == language]
            if language_results:
                avg_latency = sum(result.latency_ms for result in language_results) / len(language_results)
                rows[key] = round(avg_latency, 2)
        breakdown[language] = rows
    return breakdown



def build_judge_breakdown(judge_scores_by_model: dict[str, list[JudgeResult]]) -> dict[str, dict[str, float]]:
    categories = sorted({score.category for scores in judge_scores_by_model.values() for score in scores if score.category})
    breakdown: dict[str, dict[str, float]] = {}
    for category in categories:
        rows: dict[str, float] = {}
        for key, scores in sorted(judge_scores_by_model.items()):
            category_scores = [score.overall_score for score in scores if score.category == category]
            if category_scores:
                rows[key] = round(sum(category_scores) / len(category_scores), 2)
        breakdown[category] = rows
    return breakdown



def build_comparative_markdown(
    summaries: list[EvalSummary],
    category_breakdown: dict[str, dict[str, float]],
    language_breakdown: dict[str, dict[str, float]] | None = None,
    judge_breakdown: dict[str, dict[str, float]] | None = None,
) -> str:
    ranking_rows = build_ranking_rows(summaries)
    lines = ["# Batch model comparison", ""]

    if ranking_rows:
        best = ranking_rows[0]
        fastest = min(ranking_rows, key=lambda row: float(row["avg_latency_ms"]))
        cheapest = min(ranking_rows, key=lambda row: float(row["estimated_total_cost"]))
        lines.extend(
            [
                "## Key findings",
                f"- Top score: {best['provider']} / {best['model']} ({best['avg_score']})",
                f"- Fastest average latency: {fastest['provider']} / {fastest['model']} ({fastest['avg_latency_ms']} ms)",
                f"- Lowest estimated total cost: {cheapest['provider']} / {cheapest['model']} ({cheapest['estimated_total_cost']})",
                "",
            ]
        )

    lines.extend(
        [
            "## Overall ranking",
            "| Rank | Provider | Model | Avg score | Avg latency (ms) | Estimated total cost | Queries |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in ranking_rows:
        lines.append(
            f"| {row['rank']} | {row['provider']} | {row['model']} | {row['avg_score']} | {row['avg_latency_ms']} | {row['estimated_total_cost']} | {row['total_queries']} |"
        )
    if not ranking_rows:
        lines.append("| - | - | - | - | - | - | - |")

    lines.extend(["", "## Category breakdown"])
    if category_breakdown:
        for category, rows in category_breakdown.items():
            lines.extend(["", f"### {category}", "| Model | Avg score |", "| --- | --- |"])
            if rows:
                sorted_rows = sorted(rows.items(), key=lambda item: (-item[1], item[0]))
                for key, avg_score in sorted_rows:
                    lines.append(f"| {key} | {avg_score} |")
    else:
        lines.extend(["No category score data available.", ""])

    if judge_breakdown:
        lines.extend(["", "## Judge breakdown"])
        for category, rows in judge_breakdown.items():
            lines.extend(["", f"### {category}", "| Model | Judge avg score |", "| --- | --- |"])
            if rows:
                sorted_rows = sorted(rows.items(), key=lambda item: (-item[1], item[0]))
                for key, avg_score in sorted_rows:
                    lines.append(f"| {key} | {avg_score} |")

    lines.extend(["", "## Language breakdown (avg latency ms)"])
    if not language_breakdown:
        lines.extend(["No language breakdown data available.", ""])
        return "\n".join(lines)

    for language, rows in language_breakdown.items():
        lines.extend(["", f"### {language}", "| Model | Avg latency (ms) |", "| --- | --- |"])
        if rows:
            sorted_rows = sorted(rows.items(), key=lambda item: (item[1], item[0]))
            for key, avg_latency in sorted_rows:
                lines.append(f"| {key} | {avg_latency} |")

    lines.append("")
    return "\n".join(lines)



def write_comparative_report(path: str | Path, markdown: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
