import asyncio
from pathlib import Path

from yoyo.evals.routing import evaluate_routing_case, normalize_expected_intent, run_routing_benchmark_sync
from yoyo.modules.qa.schemas import IntentRouterFallbackResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "evals/datasets/routing_benchmark_cases_zh_hard_v1.json"


def test_normalize_expected_intent_maps_planner_handoff() -> None:
    assert normalize_expected_intent("planner_handoff") == "manual_route_edit_redirect"
    assert normalize_expected_intent("live_info") == "live_info"


def test_run_routing_benchmark_rules_only_produces_zh_hard_summary() -> None:
    results, summary = run_routing_benchmark_sync(
        DATASET,
        candidate_name="rules_only",
        fallback_enabled=False,
    )

    assert len(results) == 72
    assert summary["candidate_name"] == "rules_only"
    assert summary["dataset_name"] == "routing_benchmark_cases_zh_hard_v1"
    assert summary["total_cases"] == len(results)
    assert summary["per_intent"]["manual_route_edit_redirect"]["total"] == 12
    assert summary["per_bucket"]["attraction_explain_family_zh"]["total"] == 1
    assert "live_vs_attraction_conflict" in summary["per_conflict_type"]
    assert "out_of_scope" in summary["confusion"]


def test_run_routing_benchmark_uses_fallback_when_enabled() -> None:
    async def fake_resolver(**kwargs):
        return IntentRouterFallbackResult(intent="live_info", confidence=0.91, reason="test_override", weather_location_name=None), {
            "llm": {
                "provider": "dashscope",
                "model": "qwen-flash",
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
                "estimated_total_cost": 0.0012,
                "error": None,
            }
        }

    results, summary = run_routing_benchmark_sync(
        DATASET,
        candidate_name="rules_plus_fallback_qwen_flash",
        fallback_enabled=True,
        fallback_provider="dashscope",
        fallback_model="qwen-flash",
        fallback_resolver=fake_resolver,
    )

    target = next(item for item in results if item["case_id"] == "RZH-LI-001")
    assert target["needs_fallback"] is True
    assert target["fallback_used"] is True
    assert target["final_intent"] == "live_info"
    assert target["fallback_provider"] == "dashscope"
    assert target["fallback_model"] == "qwen-flash"
    assert summary["fallback_used_cases"] >= 1
    assert summary["estimated_total_cost"] > 0


def test_run_routing_benchmark_keeps_rule_result_when_fallback_invalid() -> None:
    async def fake_resolver(**kwargs):
        return None, {"llm": {"provider": "dashscope", "model": "bad-model", "usage": {}, "error": {"type": "invalid_json"}}}

    results, summary = run_routing_benchmark_sync(
        DATASET,
        candidate_name="rules_plus_invalid_fallback",
        fallback_enabled=True,
        fallback_provider="dashscope",
        fallback_model="bad-model",
        fallback_resolver=fake_resolver,
    )

    target = next(item for item in results if item["case_id"] == "RZH-LI-001")
    assert target["needs_fallback"] is True
    assert target["fallback_used"] is False
    assert target["rule_intent"] == target["final_intent"]
    assert summary["fallback_used_cases"] == 0


def test_evaluate_routing_case_hard_deny_overrides_rule_result() -> None:
    row = asyncio.run(
        evaluate_routing_case(
            {
                "case_id": "hard-deny-1",
                "language": "zh",
                "query": "给我写个 Python 排序算法。",
                "expected_intent": "out_of_scope",
            },
            candidate_name="rules_only",
            fallback_enabled=False,
        )
    )

    assert row["hard_deny"] is True
    assert row["final_intent"] == "out_of_scope"
    assert row["fallback_used"] is False


def test_evaluate_routing_case_uses_query_zh_for_non_chinese_cases() -> None:
    row = asyncio.run(
        evaluate_routing_case(
            {
                "case_id": "non-zh-1",
                "language": "en",
                "query": "Is the Forbidden City open today and do I need a reservation?",
                "query_zh": "故宫今天开放吗，需要预约吗？",
                "expected_intent": "live_info",
            },
            candidate_name="rules_only",
            fallback_enabled=False,
        )
    )

    assert row["query"] == "Is the Forbidden City open today and do I need a reservation?"
    assert row["routed_query"] == "故宫今天开放吗，需要预约吗？"
    assert row["rule_intent"] == "live_info"
