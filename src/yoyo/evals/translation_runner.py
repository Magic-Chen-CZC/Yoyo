from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

from yoyo.evals.translation_scoring import score_routing_case, score_translation_case
from yoyo.modules.qa.intent_router import score_intent
from yoyo.modules.translator.service import preprocess_query, translate_for_qa


async def run_translation_benchmark(
    *,
    suite: str,
    dataset_path: str | Path,
    provider: str,
    model: str,
    timeout_seconds: float,
    output_path: str | Path,
    summary_output_path: str | Path,
    bilingual_enabled: bool = True,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    dataset = _load_dataset(dataset_path)
    cases = _validated_cases(dataset, suite=suite)
    dataset_name = str(dataset.get("dataset_name") or Path(dataset_path).stem)
    dataset_version = str(dataset.get("dataset_version") or "unspecified")
    run_id = f"translation-{provider}-{suite}-{uuid.uuid4().hex[:8]}"
    run_started_at = datetime.now(UTC).isoformat()
    results: list[dict[str, object]] = []

    for case in cases:
        case_id = str(case["id"])
        question_type = str(case["question_type"])
        category = str(case["category"])
        direction = str(case["direction"])
        user_language = str(case["user_language"])
        if suite == "product_translation":
            translator_result = await translate_for_qa(
                query=str(case["query"]),
                user_language=user_language,
                provider=provider,
                model=model,
                timeout_seconds=timeout_seconds,
                enabled=True,
                bilingual_enabled=bilingual_enabled,
            )
            score = score_translation_case(case, {
                "response_text": translator_result.text,
                "user_visible_lines": translator_result.user_visible_lines,
            })
            results.append(
                {
                    "run_id": run_id,
                    "run_started_at": run_started_at,
                    "suite": suite,
                    "dataset_name": dataset_name,
                    "dataset_version": dataset_version,
                    "case_id": case_id,
                    "question_type": question_type,
                    "category": category,
                    "direction": direction,
                    "provider": provider,
                    "model": model,
                    "query": case["query"],
                    "response_text": translator_result.text,
                    "status": translator_result.status,
                    "reason": translator_result.reason,
                    "execution_path": translator_result.execution_path,
                    "latency_ms": translator_result.latency_ms,
                    "source_language": translator_result.source_language,
                    "target_language": translator_result.target_language,
                    "user_language": user_language,
                    "mode": translator_result.mode,
                    "prompt_tokens": translator_result.prompt_tokens,
                    "completion_tokens": translator_result.completion_tokens,
                    "total_tokens": translator_result.total_tokens,
                    "estimated_input_cost": translator_result.estimated_input_cost,
                    "estimated_output_cost": translator_result.estimated_output_cost,
                    "estimated_total_cost": translator_result.estimated_total_cost,
                    "llm_error": translator_result.llm_error,
                    "raw_text": translator_result.raw_text,
                    "structured_output_valid": translator_result.structured_output_valid,
                    "attempt_count": translator_result.attempt_count,
                    "retry_performed": translator_result.retry_performed,
                    "attempts": translator_result.attempts,
                    "user_visible_lines": translator_result.user_visible_lines,
                    "display_blocks": [block.model_dump() for block in translator_result.display_blocks],
                    "score": score.get("score"),
                    "max_score": score.get("max_score"),
                    "passed_checks": score.get("passed_checks"),
                    "failed_checks": score.get("failed_checks"),
                    "score_detail": score,
                    "case_metadata": case,
                }
            )
        elif suite == "routing_preprocess":
            translator_result = await preprocess_query(
                query=str(case["query"]),
                source_language=str(case["source_language"]),
                target_language=str(case["target_language"]),
                provider=provider,
                model=model,
                timeout_seconds=timeout_seconds,
                enabled=True,
            )
            downstream = score_intent(translator_result.text, raw_query=str(case["query"]))
            score = score_routing_case(case, {
                "response_text": translator_result.text,
                "downstream_intent": downstream.get("intent"),
            })
            results.append(
                {
                    "run_id": run_id,
                    "run_started_at": run_started_at,
                    "suite": suite,
                    "dataset_name": dataset_name,
                    "dataset_version": dataset_version,
                    "case_id": case_id,
                    "question_type": question_type,
                    "category": category,
                    "direction": direction,
                    "provider": provider,
                    "model": model,
                    "query": case["query"],
                    "response_text": translator_result.text,
                    "status": translator_result.status,
                    "reason": translator_result.reason,
                    "execution_path": translator_result.execution_path,
                    "latency_ms": translator_result.latency_ms,
                    "source_language": translator_result.source_language,
                    "target_language": translator_result.target_language,
                    "user_language": user_language,
                    "mode": translator_result.mode,
                    "prompt_tokens": translator_result.prompt_tokens,
                    "completion_tokens": translator_result.completion_tokens,
                    "total_tokens": translator_result.total_tokens,
                    "estimated_input_cost": translator_result.estimated_input_cost,
                    "estimated_output_cost": translator_result.estimated_output_cost,
                    "estimated_total_cost": translator_result.estimated_total_cost,
                    "llm_error": translator_result.llm_error,
                    "raw_text": translator_result.raw_text,
                    "structured_output_valid": translator_result.structured_output_valid,
                    "attempt_count": translator_result.attempt_count,
                    "retry_performed": translator_result.retry_performed,
                    "attempts": translator_result.attempts,
                    "downstream_intent": downstream.get("intent"),
                    "downstream_confidence": downstream.get("confidence"),
                    "score": score.get("score"),
                    "max_score": score.get("max_score"),
                    "passed_checks": score.get("passed_checks"),
                    "failed_checks": score.get("failed_checks"),
                    "score_detail": score,
                    "case_metadata": case,
                }
            )
        else:
            raise ValueError(f"unsupported translation benchmark suite: {suite}")

    _write_json(output_path, results)
    summary = _summarize_results(suite, provider, model, results, run_id=run_id, dataset_name=dataset_name, dataset_version=dataset_version)
    _write_json(summary_output_path, summary)
    return results, summary


def run_translation_benchmark_sync(
    *,
    suite: str,
    dataset_path: str | Path,
    provider: str,
    model: str,
    timeout_seconds: float,
    output_path: str | Path,
    summary_output_path: str | Path,
    bilingual_enabled: bool = True,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    return asyncio.run(
        run_translation_benchmark(
            suite=suite,
            dataset_path=dataset_path,
            provider=provider,
            model=model,
            timeout_seconds=timeout_seconds,
            output_path=output_path,
            summary_output_path=summary_output_path,
            bilingual_enabled=bilingual_enabled,
        )
    )


def _load_dataset(path: str | Path) -> dict[str, object]:
    dataset_path = Path(path)
    text = dataset_path.read_text(encoding="utf-8")
    if dataset_path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _validated_cases(dataset: dict[str, object], *, suite: str) -> list[dict[str, object]]:
    cases = dataset.get("cases") or []
    if not isinstance(cases, list):
        raise ValueError("translation benchmark dataset must contain a list of cases")

    validated: list[dict[str, object]] = []
    allowed_question_types = {
        str(item)
        for item in (dataset.get("question_types") or [])
        if str(item).strip()
    }

    for raw_case in cases:
        if not isinstance(raw_case, dict):
            raise ValueError("translation benchmark case must be an object")
        case = dict(raw_case)
        case_id = str(case.get("id") or "<missing-id>")

        required_fields = [
            "id",
            "query",
            "question_type",
            "category",
            "direction",
            "source_language",
            "target_language",
            "user_language",
        ]
        if suite == "routing_preprocess":
            required_fields.append("expected_intent")

        for field in required_fields:
            value = case.get(field)
            if value is None or str(value).strip() == "":
                raise ValueError(f"missing required field `{field}` in case `{case_id}`")

        question_type = str(case["question_type"])
        if allowed_question_types and question_type not in allowed_question_types:
            raise ValueError(f"unknown question_type `{question_type}` in case `{case_id}`")

        source_language = str(case["source_language"])
        target_language = str(case["target_language"])
        expected_direction = _expected_direction(source_language, target_language, bool(case.get("bilingual_for_display")))
        if str(case["direction"]) != expected_direction:
            raise ValueError(
                f"invalid direction `{case['direction']}` in case `{case_id}`; expected `{expected_direction}`"
            )

        category = str(case["category"])
        bilingual_for_display = bool(case.get("bilingual_for_display"))
        user_language = str(case["user_language"])
        if category == "direct_translation" and user_language != source_language:
            raise ValueError(
                f"product translation case `{case_id}` must align user_language with source_language under the current explicit-translation policy"
            )
        if bilingual_for_display and category != "bilingual_display":
            raise ValueError(
                f"case `{case_id}` sets bilingual_for_display=true but category is `{category}`"
            )
        if not bilingual_for_display and str(case["direction"]).endswith("_display"):
            raise ValueError(
                f"case `{case_id}` uses display direction `{case['direction']}` without bilingual_for_display=true"
            )

        if suite == "routing_preprocess" and target_language != "zh":
            raise ValueError(f"routing case `{case_id}` must target zh, got `{target_language}`")

        if _is_extreme_multilingual_query(str(case["query"])):
            raise ValueError(f"case `{case_id}` is too multilingual for the strict translation benchmark dataset")

        validated.append(case)

    return validated


def _expected_direction(source_language: str, target_language: str, bilingual_for_display: bool) -> str:
    suffix = "_display" if bilingual_for_display else ""
    return f"{source_language}_to_{target_language}{suffix}"


def _is_extreme_multilingual_query(query: str) -> bool:
    stripped = query.strip()
    source_text = stripped
    for separator in [":", "："]:
        if separator in stripped:
            source_text = stripped.split(separator, 1)[1].strip()
            break

    script_count = 0
    if re.search(r"[一-鿿]", source_text):
        script_count += 1
    if re.search(r"[฀-๿]", source_text):
        script_count += 1
    if re.search(r"[က-႟]", source_text):
        script_count += 1
    if re.search(r"[ក-៿]", source_text):
        script_count += 1
    if re.search(r"[ກ-໿]", source_text):
        script_count += 1
    if re.search(r"[A-Za-z]", source_text):
        script_count += 1
    return script_count >= 3


def _write_json(path: str | Path, payload: object) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _summarize_results(
    suite: str,
    provider: str,
    model: str,
    results: list[dict[str, object]],
    *,
    run_id: str,
    dataset_name: str,
    dataset_version: str,
) -> dict[str, object]:
    total = len(results)
    avg_latency = sum(float(item.get("latency_ms") or 0.0) for item in results) / total if total else 0.0
    avg_score = sum(float(item.get("score") or 0.0) for item in results) / total if total else 0.0
    degraded = sum(1 for item in results if item.get("status") != "ok")
    sum_prompt_tokens = sum(int(item.get("prompt_tokens") or 0) for item in results)
    sum_completion_tokens = sum(int(item.get("completion_tokens") or 0) for item in results)
    sum_total_tokens = sum(int(item.get("total_tokens") or 0) for item in results)
    estimated_total_cost = round(sum(float(item.get("estimated_total_cost") or 0.0) for item in results), 8)
    execution_paths: dict[str, int] = {}
    by_case_category: dict[str, dict[str, float]] = {}
    by_language: dict[str, dict[str, float]] = {}
    by_direction: dict[str, dict[str, float]] = {}
    by_question_type: dict[str, dict[str, float]] = {}

    for item in results:
        key = str(item.get("execution_path") or "unknown")
        execution_paths[key] = execution_paths.get(key, 0) + 1
        for bucket_name, bucket_key in [
            (str(item.get("category") or "uncategorized"), by_case_category),
            (str(item.get("target_language") or item.get("source_language") or "unknown"), by_language),
            (str(item.get("direction") or "unknown"), by_direction),
            (str(item.get("question_type") or "uncategorized"), by_question_type),
        ]:
            row = bucket_key.setdefault(bucket_name, {"count": 0, "score_sum": 0.0, "latency_sum": 0.0})
            row["count"] += 1
            row["score_sum"] += float(item.get("score") or 0.0)
            row["latency_sum"] += float(item.get("latency_ms") or 0.0)

    def _finalize_bucket(bucket: dict[str, dict[str, float]]) -> dict[str, dict[str, float | int]]:
        return {
            key: {
                "count": int(value["count"]),
                "avg_score": round(value["score_sum"] / value["count"], 2) if value["count"] else 0.0,
                "avg_latency_ms": round(value["latency_sum"] / value["count"], 2) if value["count"] else 0.0,
            }
            for key, value in bucket.items()
        }

    return {
        "run_id": run_id,
        "suite": suite,
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "provider": provider,
        "model": model,
        "total_cases": total,
        "avg_latency_ms": round(avg_latency, 2),
        "avg_score": round(avg_score, 2),
        "degraded_cases": degraded,
        "sum_prompt_tokens": sum_prompt_tokens,
        "sum_completion_tokens": sum_completion_tokens,
        "sum_total_tokens": sum_total_tokens,
        "estimated_total_cost": estimated_total_cost,
        "execution_paths": execution_paths,
        "category_breakdown": _finalize_bucket(by_case_category),
        "by_language": _finalize_bucket(by_language),
        "by_direction": _finalize_bucket(by_direction),
        "by_question_type": _finalize_bucket(by_question_type),
    }
