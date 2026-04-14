# 这份测试偏向 Eval 主流程验证：题目生成、执行、汇总、报告构建。
from pathlib import Path

from yoyo.evals.query_generator import generate_queries, load_query_templates
from yoyo.evals.reporting import build_category_breakdown, build_comparative_markdown, build_ranking_rows
from yoyo.evals.runner import run_evaluation_sync
from yoyo.evals.schemas import EvalScore, EvalSummary

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_generate_queries_from_templates() -> None:
    template_data = load_query_templates(PROJECT_ROOT / "evals/datasets/query_templates.yaml")
    queries = generate_queries(template_data)

    assert len(queries) > 0
    assert any(query.category == "attraction_explain" for query in queries)
    assert any(query.language == "en" for query in queries)


def test_run_eval_outputs_results_file(tmp_path: Path) -> None:
    output_path = tmp_path / "results.json"
    results, summary = run_evaluation_sync(
        provider="anthropic",
        model="claude-sonnet-4-6",
        template_path=PROJECT_ROOT / "evals/datasets/query_templates.yaml",
        output_path=output_path,
    )

    assert len(results) > 0
    assert summary.total_queries == len(results)
    assert output_path.exists()


def test_explicit_english_query_dataset_count() -> None:
    template_data = load_query_templates(PROJECT_ROOT / "evals/datasets/english_queries_81.json")
    queries = generate_queries(template_data)

    assert len(queries) == 81
    assert all(query.language == "en" for query in queries)


def test_reporting_builds_ranking_and_category_breakdown() -> None:
    summaries = [
        EvalSummary(
            provider="openrouter",
            model="model-a",
            total_queries=10,
            avg_latency_ms=900,
            estimated_total_input_cost=0.1,
            estimated_total_output_cost=0.2,
            estimated_total_cost=0.3,
            avg_score=4.4,
        ),
        EvalSummary(
            provider="openrouter",
            model="model-b",
            total_queries=10,
            avg_latency_ms=700,
            estimated_total_input_cost=0.08,
            estimated_total_output_cost=0.1,
            estimated_total_cost=0.18,
            avg_score=4.8,
        ),
    ]
    scores_by_model = {
        "openrouter:model-a": [
            EvalScore(
                query_id="1",
                provider="openrouter",
                model="model-a",
                category="live_info",
                score=4,
                max_score=5,
                rationale="ok",
            ),
            EvalScore(
                query_id="2",
                provider="openrouter",
                model="model-a",
                category="trip_assistant",
                score=5,
                max_score=5,
                rationale="ok",
            ),
        ],
        "openrouter:model-b": [
            EvalScore(
                query_id="3",
                provider="openrouter",
                model="model-b",
                category="live_info",
                score=5,
                max_score=5,
                rationale="ok",
            ),
            EvalScore(
                query_id="4",
                provider="openrouter",
                model="model-b",
                category="trip_assistant",
                score=4,
                max_score=5,
                rationale="ok",
            ),
        ],
    }

    ranking_rows = build_ranking_rows(summaries)
    category_breakdown = build_category_breakdown(scores_by_model)
    markdown = build_comparative_markdown(summaries, category_breakdown)

    assert ranking_rows[0]["model"] == "model-b"
    assert category_breakdown["live_info"]["openrouter:model-b"] == 5.0
    assert "# Batch model comparison" in markdown
    assert "## Overall ranking" in markdown
    assert "### live_info" in markdown
    assert "openrouter:model-b" in markdown
