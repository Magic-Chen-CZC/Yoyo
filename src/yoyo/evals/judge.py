from __future__ import annotations

import json
import time

from yoyo.evals.judge_prompts import JUDGE_VERSION, RUBRIC_VERSION, build_judge_prompt
from yoyo.evals.providers import get_provider
from yoyo.evals.schemas import EvalResult, HardCheckResult, JudgeResult



def judge_result(
    result: EvalResult,
    hard_check: HardCheckResult,
    *,
    judge_provider: str = "openrouter",
    judge_model: str = "openai/gpt-5.4-mini",
) -> JudgeResult:
    provider = get_provider(judge_provider, judge_model)
    prompt = build_judge_prompt(result, hard_check)
    started = time.perf_counter()
    raw = provider.generate(prompt)
    if hasattr(raw, "__await__"):
        raise RuntimeError("judge_result must be called with sync-compatible provider wrapper")
    raise RuntimeError("Unexpected non-async provider usage")


async def judge_result_async(
    result: EvalResult,
    hard_check: HardCheckResult,
    *,
    judge_provider: str = "openrouter",
    judge_model: str = "openai/gpt-5.4-mini",
) -> JudgeResult:
    provider = get_provider(judge_provider, judge_model)
    prompt = build_judge_prompt(result, hard_check)
    started = time.perf_counter()
    raw = await provider.generate(prompt)
    latency_ms = (time.perf_counter() - started) * 1000
    text = str(raw.get("text") or "")
    usage = raw.get("usage") or {}
    parsed = _parse_json(text)
    if parsed is None:
        parsed = {
            "overall_score": 0.0,
            "decision": "judge_parse_failed",
            "confidence": 0.0,
            "dimension_scores": {},
            "dimension_rationales": {},
            "issues": [{"severity": "high", "code": "judge_parse_failed", "message": "Judge output was not valid JSON."}],
        }
    return JudgeResult(
        query_id=result.query_id,
        provider=result.provider,
        model=result.model,
        category=str(result.metadata.get("category", "")),
        judge_provider=judge_provider,
        judge_model=judge_model,
        judge_version=JUDGE_VERSION,
        rubric_version=RUBRIC_VERSION,
        overall_score=float(parsed.get("overall_score", 0.0)),
        max_score=5.0,
        decision=str(parsed.get("decision", "unknown")),
        confidence=float(parsed.get("confidence", 0.0)),
        dimension_scores=_normalize_dimension_scores(parsed.get("dimension_scores", {})),
        dimension_rationales=_normalize_dimension_rationales(parsed.get("dimension_rationales", {})),
        issues=_normalize_issues(parsed.get("issues", [])),
        hard_constraint_summary={
            "passed": hard_check.passed,
            "failed_checks": hard_check.failed_checks,
            "score_cap": hard_check.score_cap,
        },
        judge_latency_ms=latency_ms,
        judge_prompt_tokens=usage.get("prompt_tokens"),
        judge_completion_tokens=usage.get("completion_tokens"),
        judge_total_tokens=usage.get("total_tokens"),
        judge_total_cost=usage.get("cost"),
        raw_judge_text=text,
    )



def _parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None



def _normalize_dimension_scores(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, float] = {}
    for key, item in value.items():
        try:
            normalized[str(key)] = float(item)
        except Exception:
            continue
    return normalized



def _normalize_dimension_rationales(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}



def _normalize_issues(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, dict):
            normalized.append(
                {
                    'severity': str(item.get('severity', 'medium')),
                    'code': str(item.get('code', 'unspecified')),
                    'message': str(item.get('message', '')),
                }
            )
        elif isinstance(item, str):
            normalized.append(
                {
                    'severity': 'medium',
                    'code': 'freeform_issue',
                    'message': item,
                }
            )
    return normalized
