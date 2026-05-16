from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_runner_module():
    module_path = Path(__file__).resolve().parents[1] / "evals" / "run_e2e_qa_benchmark.py"
    spec = importlib.util.spec_from_file_location("run_e2e_qa_benchmark", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_e2e_benchmark_latency_fields_flatten_metadata() -> None:
    runner = _load_runner_module()
    metadata = {
        "latency_ms": {
            "preprocess_ms": 10,
            "routing_ms": 20,
            "context_build_ms": 30,
            "context_build_breakdown_ms": {
                "attraction_lookup_ms": 3,
                "rag_lookup_ms": 12,
                "weather_target_source": "fallback",
                "navigation_slot_source": "rule",
                "rag_needed": True,
            },
            "generation_ms": 40,
            "postprocess_ms": 50,
            "total_ms": 150,
        }
    }

    fields = runner._latency_fields(metadata)

    assert fields["preprocess_ms"] == 10
    assert fields["routing_ms"] == 20
    assert fields["context_build_ms"] == 30
    assert fields["generation_ms"] == 40
    assert fields["postprocess_ms"] == 50
    assert fields["total_ms"] == 150
    assert fields["attraction_lookup_ms"] == 3
    assert fields["rag_lookup_ms"] == 12
    assert fields["weather_target_source"] == "fallback"
    assert fields["navigation_slot_source"] == "rule"
    assert fields["rag_needed"] is True


def test_e2e_benchmark_summary_groups_stage_latency() -> None:
    runner = _load_runner_module()
    rows = [
        {
            "case_id": "c1",
            "language": "zh",
            "category": "attraction_explain",
            "expected_intent": "attraction_explain",
            "operation": "sql_grounded_generation",
            "score": 5.0,
            "decision": "pass",
            "intent_correct": True,
            "latency_ms": 100.0,
            "preprocess_ms": 0,
            "routing_ms": 5,
            "context_build_ms": 10,
            "generation_ms": 70,
            "postprocess_ms": 0,
            "rag_lookup_ms": 0,
        },
        {
            "case_id": "c2",
            "language": "en",
            "category": "trip_assistant",
            "expected_intent": "trip_assistant",
            "operation": "preprocess_session_generation_postprocess",
            "score": 4.0,
            "decision": "pass",
            "intent_correct": True,
            "latency_ms": 300.0,
            "preprocess_ms": 40,
            "routing_ms": 20,
            "context_build_ms": 30,
            "generation_ms": 120,
            "postprocess_ms": 50,
            "rag_lookup_ms": 0,
        },
    ]

    summary = runner._build_summary(
        dataset={"dataset_name": "demo", "dataset_version": "v1"},
        run_id="run-1",
        model="qwen-turbo",
        provider="dashscope",
        base_url="http://127.0.0.1:8000",
        rows=rows,
    )

    assert summary["avg_latency_ms"] == 200.0
    assert summary["p50_latency_ms"] == 200.0
    assert summary["p95_latency_ms"] == 290.0
    assert summary["stage_latency_ms"]["generation_ms"] == 95.0
    assert summary["by_language"][0]["language"] == "en"
    assert summary["by_language"][0]["avg_preprocess_ms"] == 40.0
    assert summary["by_category"][0]["category"] == "attraction_explain"
    assert summary["by_operation"][1]["operation"] == "sql_grounded_generation"
