from pathlib import Path

from yoyo.evals.query_generator import generate_queries, load_query_templates
from yoyo.evals.runner import run_evaluation_sync


def test_generate_queries_from_templates() -> None:
    template_data = load_query_templates("evals/datasets/query_templates.yaml")
    queries = generate_queries(template_data)

    assert len(queries) > 0
    assert any(query.category == "attraction_explain" for query in queries)
    assert any(query.language == "en" for query in queries)


def test_run_eval_outputs_results_file(tmp_path: Path) -> None:
    output_path = tmp_path / "results.json"
    results, summary = run_evaluation_sync(
        provider="anthropic",
        model="claude-sonnet-4-6",
        template_path="evals/datasets/query_templates.yaml",
        output_path=output_path,
    )

    assert len(results) > 0
    assert summary.total_queries == len(results)
    assert output_path.exists()


def test_explicit_english_query_dataset_count() -> None:
    template_data = load_query_templates("evals/datasets/english_queries_81.json")
    queries = generate_queries(template_data)

    assert len(queries) == 81
    assert all(query.language == "en" for query in queries)
