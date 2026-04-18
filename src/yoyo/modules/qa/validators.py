# validators.py 是 QA 的轻量质检层。
# 当前阶段按 intent 做最基础的结构/质量校验，但不阻断主流程。
from typing import Any



def validate_answer(intent: str, answer: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    checks: list[dict[str, object]] = []

    checks.append({"name": "non_empty", "passed": bool(answer.strip())})

    if intent == "translation":
        checks.append({"name": "no_guided_mode_placeholder", "passed": "guided mode" not in answer.lower()})
    if intent == "live_info":
        checks.append(
            {
                "name": "same_day_verification_hint",
                "passed": any(token in answer.lower() for token in ["verify", "check", "official"]),
            }
        )
    if intent == "trip_assistant":
        current_stop_name = _nested_str(metadata, "context", "session_context", "current_stop_name")
        next_stop_name = _nested_str(metadata, "context", "session_context", "next_stop_name")
        route_aware = any(
            token in answer.lower()
            for token in ["current", "next", "route", "stop", "head toward", "active stop"]
        )
        references_known_stop = any(
            stop_name and stop_name.lower() in answer.lower()
            for stop_name in [current_stop_name, next_stop_name]
        )
        checks.append(
            {
                "name": "route_aware_trip_guidance",
                "passed": route_aware or references_known_stop,
            }
        )
    if intent == "attraction_explain":
        retrieval_name = _nested_str(metadata, "retrieval", "name")
        degraded = bool(metadata.get("degraded"))
        grounded_signal = any(token in answer.lower() for token in ["history", "visitor tip", "highlight"]) or (
            bool(retrieval_name) and retrieval_name.lower() in answer.lower()
        )
        checks.append(
            {
                "name": "grounded_attraction_answer",
                "passed": grounded_signal or degraded,
            }
        )
    valid = all(bool(check["passed"]) for check in checks)
    return {
        "intent": intent,
        "valid": valid,
        "checks": checks,
    }



def _nested_str(data: dict[str, Any], *keys: str) -> str | None:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    if isinstance(current, str):
        return current
    return None
