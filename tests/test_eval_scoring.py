# 这份测试重点看“评分规则是否符合预期”。
# 很适合帮助理解 scoring.py 到底在奖励什么、惩罚什么。
from pathlib import Path

from yoyo.evals.batch import run_batch_evaluation
from yoyo.evals.scoring import score_result, score_results
from yoyo.evals.schemas import EvalResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_score_results_returns_scores() -> None:
    results = [
        EvalResult(
            query_id="q1",
            provider="anthropic",
            model="claude-sonnet-4-6",
            prompt="Explain why Tiananmen Square is important",
            response_text="Tiananmen Square is an important Beijing landmark with major historical meaning for visitors.",
            latency_ms=10,
            metadata={"category": "attraction_explain", "language": "en"},
        )
    ]

    scores = score_results(results)
    assert len(scores) == 1
    assert scores[0].score >= 1
    assert scores[0].category == "attraction_explain"


def test_live_info_strong_answer_scores_higher_than_weak_answer() -> None:
    strong = EvalResult(
        query_id="q-live-strong",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt="What should I check before visiting the Forbidden City today?",
        response_text=(
            "Check the latest official ticket and reservation notices today, verify opening hours, "
            "and confirm whether weather or transport disruptions could change access."
        ),
        latency_ms=10,
        metadata={"category": "live_info", "language": "en"},
    )
    weak = EvalResult(
        query_id="q-live-weak",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt="What should I check before visiting the Forbidden City today?",
        response_text="The Forbidden City is famous and many tourists go there.",
        latency_ms=10,
        metadata={"category": "live_info", "language": "en"},
    )

    strong_score = score_result(strong)
    weak_score = score_result(weak)

    assert strong_score.score > weak_score.score
    assert "official" in strong_score.rationale.lower()


def test_trip_assistant_route_aware_answer_scores_higher_than_generic_answer() -> None:
    route_aware = EvalResult(
        query_id="q-trip-aware",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt="Given this itinerary, what should I do after Tiananmen Square?",
        response_text="After Tiananmen Square, head to the Forbidden City as your next stop and keep the pace easy to reduce walking fatigue.",
        latency_ms=10,
        metadata={"category": "trip_assistant", "language": "en"},
    )
    generic = EvalResult(
        query_id="q-trip-generic",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt="Given this itinerary, what should I do after Tiananmen Square?",
        response_text="Beijing is a great city with many attractions.",
        latency_ms=10,
        metadata={"category": "trip_assistant", "language": "en"},
    )

    route_aware_score = score_result(route_aware)
    generic_score = score_result(generic)

    assert route_aware_score.score > generic_score.score
    assert "route progression" in route_aware_score.rationale.lower()


def test_translation_meta_explanation_is_penalized() -> None:
    direct = EvalResult(
        query_id="q-translation-direct",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt="Translate this into polite English: 这个景点几点关门",
        response_text="Could you tell me what time this attraction closes?",
        latency_ms=10,
        metadata={"category": "translation", "language": "en"},
    )
    meta = EvalResult(
        query_id="q-translation-meta",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt="Translate this into polite English: 这个景点几点关门",
        response_text="Translation: What time does this attraction close in English?",
        latency_ms=10,
        metadata={"category": "translation", "language": "en"},
    )

    direct_score = score_result(direct)
    meta_score = score_result(meta)

    assert direct_score.score > meta_score.score
    assert "meta explanation" in meta_score.rationale.lower()


def test_batch_eval_returns_summaries(tmp_path: Path) -> None:
    output_dir = tmp_path / "batch-results"
    summaries = run_batch_evaluation(
        model_matrix_path=PROJECT_ROOT / "evals/models.yaml",
        dataset_path=PROJECT_ROOT / "evals/datasets/query_templates.yaml",
        output_dir=output_dir,
    )

    assert len(summaries) >= 1
    assert all(summary.total_queries > 0 for summary in summaries)
    assert any(output_dir.iterdir())
