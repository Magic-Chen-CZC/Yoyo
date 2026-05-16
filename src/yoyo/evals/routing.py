from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from yoyo.modules.qa.domain_guard import evaluate_domain_support
from yoyo.modules.qa.intent_router import score_intent
from yoyo.modules.qa.router_fallback import resolve_router_fallback

RoutingCase = dict[str, Any]
RoutingResult = dict[str, Any]
FallbackResolver = Callable[..., Awaitable[tuple[Any | None, dict[str, Any]]]]

_PLANNER_HANDOFF = "planner_handoff"
_MANUAL_ROUTE_EDIT_REDIRECT = "manual_route_edit_redirect"


def normalize_expected_intent(intent: str | None) -> str | None:
    if intent == _PLANNER_HANDOFF:
        return _MANUAL_ROUTE_EDIT_REDIRECT
    return intent


def load_routing_dataset(path: str | Path) -> dict[str, Any]:
    dataset_path = Path(path)
    if dataset_path.suffix in {".yaml", ".yml"}:
        with dataset_path.open("r", encoding="utf-8") as file:
            dataset = yaml.safe_load(file)
    else:
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    return _resolve_dataset_includes(dataset, dataset_path.parent)


def _resolve_dataset_includes(dataset: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    include_paths = list(dataset.get("include_datasets") or [])
    if not include_paths:
        return dataset

    merged_cases: list[dict[str, Any]] = []
    for include_path in include_paths:
        child_path = Path(str(include_path))
        if not child_path.is_absolute():
            child_path = base_dir / child_path
        child = load_routing_dataset(child_path)
        merged_cases.extend(list(child.get("cases") or []))

    merged_cases.extend(list(dataset.get("cases") or []))
    return {
        **dataset,
        "cases": merged_cases,
        "included_case_count": len(merged_cases),
    }


def load_routing_candidates(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return list(data.get("candidates", []))


async def evaluate_routing_case(
    case: RoutingCase,
    *,
    candidate_name: str,
    fallback_enabled: bool,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
    fallback_resolver: FallbackResolver = resolve_router_fallback,
) -> RoutingResult:
    query = str(case.get("query") or "")
    language = str(case.get("language") or "en")
    history = list(case.get("history") or [])
    market = case.get("market")
    expected_intent = normalize_expected_intent(case.get("expected_intent"))
    expected_needs_fallback = case.get("expected_needs_fallback")
    routed_query = (
        str(case.get("query_zh") or query)
        if not language.lower().startswith("zh")
        else query
    )

    started = time.perf_counter()
    domain_guard = evaluate_domain_support(routed_query)
    rule_result = score_intent(routed_query, history, raw_query=query)
    fallback_result = None
    fallback_metadata: dict[str, Any] | None = None
    final_result = dict(rule_result)
    fallback_used = False

    if domain_guard.hard_deny:
        final_result = {
            **rule_result,
            "intent": "out_of_scope",
            "needs_fallback": False,
            "fallback_reason": rule_result.get("fallback_reason"),
            "out_of_scope_subtype": "general_out_of_scope",
        }
    elif domain_guard.supported and fallback_enabled and bool(rule_result.get("needs_fallback")):
        fallback_result, fallback_metadata = await fallback_resolver(
            query=routed_query,
            raw_query=query,
            pivot_query=routed_query if routed_query != query else None,
            language="zh" if routed_query != query else language,
            market=market if isinstance(market, str) else None,
            dialogue_history=history,
            rule_result=rule_result,
            session_context=dict(case.get("session_context") or {}),
            provider=fallback_provider,
            model=fallback_model,
        )
        if fallback_result is not None:
            final_result = {
                **rule_result,
                "intent": fallback_result.intent,
                "confidence": max(
                    float(rule_result.get("confidence", 0.0)),
                    fallback_result.confidence,
                ),
                "needs_fallback": False,
                "fallback_reason": rule_result.get("fallback_reason"),
            }
            fallback_used = True

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    final_intent = str(final_result.get("intent") or "out_of_scope")
    intent_correct = final_intent == expected_intent
    needs_fallback = bool(rule_result.get("needs_fallback"))
    fallback_decision_correct = None
    if isinstance(expected_needs_fallback, bool):
        fallback_decision_correct = needs_fallback == expected_needs_fallback
    false_direct_pass = not needs_fallback and not intent_correct
    routing_safe = intent_correct or (needs_fallback and expected_needs_fallback is True)
    llm = (fallback_metadata or {}).get("llm") or {}
    usage = llm.get("usage") or {}
    fallback_reason = rule_result.get("fallback_reason")

    return {
        "candidate_name": candidate_name,
        "case_id": case.get("case_id"),
        "bucket": case.get("bucket"),
        "language": language,
        "query": query,
        "raw_query": case.get("raw_query"),
        "routed_query": routed_query,
        "query_zh": case.get("query_zh"),
        "expected_intent": expected_intent,
        "expected_needs_fallback": expected_needs_fallback,
        "expected_boundary_behavior": case.get("expected_boundary_behavior"),
        "requires_session_context": bool(case.get("requires_session_context")),
        "has_same_day_signal": bool(case.get("has_same_day_signal")),
        "rule_intent": rule_result.get("intent"),
        "final_intent": final_intent,
        "intent_correct": intent_correct,
        "routing_safe": routing_safe,
        "false_direct_pass": false_direct_pass,
        "domain_supported": domain_guard.supported,
        "hard_deny": domain_guard.hard_deny,
        "needs_fallback": needs_fallback,
        "fallback_decision_correct": fallback_decision_correct,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "conflict_type": case.get("conflict_type"),
        "boundary_topic": rule_result.get("boundary_topic"),
        "out_of_scope_subtype": final_result.get("out_of_scope_subtype")
        or rule_result.get("out_of_scope_subtype"),
        "rule_confidence": rule_result.get("confidence"),
        "final_confidence": final_result.get("confidence"),
        "margin": rule_result.get("margin"),
        "runner_up_intent": rule_result.get("runner_up_intent"),
        "latency_ms": latency_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "estimated_total_cost": llm.get("estimated_total_cost") or llm.get("total_cost") or 0.0,
        "fallback_provider": llm.get("provider"),
        "fallback_model": llm.get("model"),
        "fallback_error": llm.get("error"),
        "notes": case.get("notes"),
        "label_rationale": case.get("label_rationale"),
    }


async def run_routing_benchmark(
    dataset_path: str | Path,
    *,
    candidate_name: str,
    fallback_enabled: bool,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
    fallback_resolver: FallbackResolver = resolve_router_fallback,
) -> tuple[list[RoutingResult], dict[str, Any]]:
    dataset = load_routing_dataset(dataset_path)
    cases = list(dataset.get("cases") or [])
    results = [
        await evaluate_routing_case(
            case,
            candidate_name=candidate_name,
            fallback_enabled=fallback_enabled,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            fallback_resolver=fallback_resolver,
        )
        for case in cases
    ]
    return results, summarize_routing_results(
        dataset,
        candidate_name,
        results,
        fallback_enabled=fallback_enabled,
    )


def run_routing_benchmark_sync(
    dataset_path: str | Path,
    *,
    candidate_name: str,
    fallback_enabled: bool,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
    fallback_resolver: FallbackResolver = resolve_router_fallback,
) -> tuple[list[RoutingResult], dict[str, Any]]:
    return asyncio.run(
        run_routing_benchmark(
            dataset_path,
            candidate_name=candidate_name,
            fallback_enabled=fallback_enabled,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            fallback_resolver=fallback_resolver,
        )
    )


def summarize_routing_results(
    dataset: dict[str, Any],
    candidate_name: str,
    results: list[RoutingResult],
    *,
    fallback_enabled: bool,
) -> dict[str, Any]:
    total_cases = len(results)
    correct_cases = sum(1 for item in results if item.get("intent_correct") is True)
    safe_cases = sum(1 for item in results if item.get("routing_safe") is True)
    fallback_needed = [item for item in results if item.get("needs_fallback") is True]
    fallback_used = [item for item in results if item.get("fallback_used") is True]
    direct_pass = [item for item in results if item.get("needs_fallback") is False]
    false_direct_pass = [item for item in direct_pass if item.get("intent_correct") is False]
    fallback_decision_labeled = [
        item for item in results if isinstance(item.get("expected_needs_fallback"), bool)
    ]
    fallback_decision_correct = [
        item for item in fallback_decision_labeled if item.get("fallback_decision_correct") is True
    ]
    boundary_cases = [item for item in results if item.get("boundary_topic") is not None]
    route_edit_cases = [
        item for item in results if item.get("expected_intent") == _MANUAL_ROUTE_EDIT_REDIRECT
    ]
    conflict_cases = [
        item
        for item in results
        if item.get("fallback_reason")
        in {
            "live_vs_attraction_conflict",
            "trip_vs_edit_conflict",
            "boundary_topic_conflict",
        }
    ]
    per_intent: dict[str, dict[str, float | int]] = {}
    per_bucket: dict[str, dict[str, float | int]] = {}
    per_conflict_type: dict[str, dict[str, float | int]] = {}
    confusion: dict[str, dict[str, int]] = {}

    for item in results:
        expected = str(item.get("expected_intent") or "unknown")
        predicted = str(item.get("final_intent") or "unknown")
        bucket = str(item.get("bucket") or "unknown")
        conflict_type = str(item.get("fallback_reason") or "none")
        stats = per_intent.setdefault(expected, {"total": 0, "correct": 0, "accuracy": 0.0})
        stats["total"] += 1
        bucket_stats = per_bucket.setdefault(bucket, {"total": 0, "correct": 0, "accuracy": 0.0})
        bucket_stats["total"] += 1
        conflict_stats = per_conflict_type.setdefault(
            conflict_type,
            {"total": 0, "correct": 0, "accuracy": 0.0},
        )
        conflict_stats["total"] += 1
        if expected == predicted:
            stats["correct"] += 1
            bucket_stats["correct"] += 1
            conflict_stats["correct"] += 1
        confusion.setdefault(expected, {})[predicted] = (
            confusion.setdefault(expected, {}).get(predicted, 0) + 1
        )

    for stats in per_intent.values():
        total = int(stats["total"])
        correct = int(stats["correct"])
        stats["accuracy"] = round(correct / total, 4) if total else 0.0

    for stats in per_bucket.values():
        total = int(stats["total"])
        correct = int(stats["correct"])
        stats["accuracy"] = round(correct / total, 4) if total else 0.0

    for stats in per_conflict_type.values():
        total = int(stats["total"])
        correct = int(stats["correct"])
        stats["accuracy"] = round(correct / total, 4) if total else 0.0

    def _subset_accuracy(rows: list[RoutingResult]) -> float | None:
        if not rows:
            return None
        return round(sum(1 for item in rows if item.get("intent_correct") is True) / len(rows), 4)

    return {
        "dataset_name": dataset.get("dataset_name"),
        "dataset_version": dataset.get("dataset_version"),
        "candidate_name": candidate_name,
        "fallback_enabled": fallback_enabled,
        "total_cases": total_cases,
        "correct_cases": correct_cases,
        "accuracy": round(correct_cases / total_cases, 4) if total_cases else 0.0,
        "safe_cases": safe_cases,
        "safe_accuracy": round(safe_cases / total_cases, 4) if total_cases else 0.0,
        "direct_pass_cases": len(direct_pass),
        "direct_pass_correct_cases": len(direct_pass) - len(false_direct_pass),
        "direct_pass_precision": round(
            (len(direct_pass) - len(false_direct_pass)) / len(direct_pass),
            4,
        )
        if direct_pass
        else None,
        "false_direct_pass_cases": len(false_direct_pass),
        "fallback_needed_cases": len(fallback_needed),
        "fallback_used_cases": len(fallback_used),
        "fallback_hit_rate": round(len(fallback_used) / len(fallback_needed), 4)
        if fallback_needed
        else 0.0,
        "fallback_decision_labeled_cases": len(fallback_decision_labeled),
        "fallback_decision_correct_cases": len(fallback_decision_correct),
        "fallback_decision_accuracy": round(
            len(fallback_decision_correct) / len(fallback_decision_labeled),
            4,
        )
        if fallback_decision_labeled
        else None,
        "needs_fallback_accuracy": _subset_accuracy(fallback_needed),
        "boundary_accuracy": _subset_accuracy(boundary_cases),
        "manual_route_edit_accuracy": _subset_accuracy(route_edit_cases),
        "conflict_accuracy": _subset_accuracy(conflict_cases),
        "avg_latency_ms": round(mean(item["latency_ms"] for item in results), 2)
        if results
        else 0.0,
        "estimated_total_cost": round(
            sum(float(item.get("estimated_total_cost") or 0.0) for item in results),
            8,
        ),
        "per_intent": per_intent,
        "per_bucket": per_bucket,
        "per_conflict_type": per_conflict_type,
        "confusion": confusion,
    }


def write_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
