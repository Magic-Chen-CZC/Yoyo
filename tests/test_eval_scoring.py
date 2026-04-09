from pathlib import Path

from yoyo.evals.batch import run_batch_evaluation
from yoyo.evals.scoring import score_results
from yoyo.evals.schemas import EvalResult


def test_score_results_returns_scores() -> None:
    results = [
        EvalResult(
            query_id="q1",
            provider="anthropic",
            model="claude-sonnet-4-6",
            prompt="Explain why Tiananmen Square is important",
            response_text="Tiananmen Square is important in Beijing history.",
            latency_ms=10,
            metadata={"category": "attraction_explain", "language": "en"},
        )
    ]

    scores = score_results(results)
    assert len(scores) == 1
    assert scores[0].score >= 1
    assert scores[0].category == "attraction_explain"


def test_batch_eval_returns_summaries(tmp_path: Path) -> None:
    output_dir = tmp_path / "batch-results"
    summaries = run_batch_evaluation(
        model_matrix_path="evals/models.yaml",
        dataset_path="evals/datasets/query_templates.yaml",
        output_dir=output_dir,
    )

    assert len(summaries) >= 1
    assert all(summary.total_queries > 0 for summary in summaries)
    assert any(output_dir.iterdir())
