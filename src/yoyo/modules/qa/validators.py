# validators.py 是 QA 的轻量质检层。
# 当前阶段按 intent 做最基础的结构/质量校验，但不阻断主流程。
from typing import Any



def validate_answer(intent: str, answer: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    checks: list[dict[str, object]] = []

    checks.append({"name": "non_empty", "passed": bool(answer.strip())})

    if intent == "translation":
        checks.append({"name": "no_guided_mode_placeholder", "passed": "guided mode" not in answer.lower()})
    if intent == "smalltalk":
        checks.append(
            {
                "name": "smalltalk_acknowledged",
                "passed": any(token in answer.lower() for token in ["你好", "不客气", "随时", "我在"]),
            }
        )
    if intent == "live_info":
        checks.append(
            {
                "name": "same_day_verification_hint",
                "passed": any(token in answer.lower() for token in ["verify", "check", "official", "确认", "核实", "官网", "最新信息"]),
            }
        )
    if intent == "trip_assistant":
        current_stop_name = _nested_str(metadata, "context", "session_context", "current_stop_name")
        next_stop_name = _nested_str(metadata, "context", "session_context", "next_stop_name")
        route_aware = any(
            token in answer.lower()
            for token in ["current", "next", "route", "stop", "head toward", "active stop", "当前", "下一站", "路线", "站点", "前往"]
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
    if intent == "weather_info":
        weather = _nested_str(metadata, "weather", "weather")
        temperature = _nested_str(metadata, "weather", "temperature_celsius")
        degraded = bool(metadata.get("degraded"))
        checks.append(
            {
                "name": "grounded_weather_answer",
                "passed": bool(weather or temperature) or degraded,
            }
        )
    if intent == "navigation_text":
        distance = _nested_value(metadata, "navigation", "distance_meters")
        duration = _nested_value(metadata, "navigation", "duration_seconds")
        steps = _nested_value(metadata, "navigation", "steps")
        legs = _nested_value(metadata, "navigation", "legs")
        status = _nested_str(metadata, "navigation", "status")
        degraded = bool(metadata.get("degraded"))
        checks.append(
            {
                "name": "grounded_navigation_answer",
                "passed": bool(steps) or distance is not None or duration is not None or degraded or status == "clarification",
            }
        )
        checks.append(
            {
                "name": "multi_leg_navigation_shape",
                "passed": not legs or _valid_navigation_legs(legs) or degraded or status == "clarification",
            }
        )
    if intent == "manual_route_edit_redirect":
        checks.append(
            {
                "name": "redirect_route_edit_answer",
                "passed": any(token in answer.lower() for token in ["itinerary editor", "route", "stop", "行程编辑器", "路线", "站点"]),
            }
        )
    if intent == "out_of_scope" and metadata.get("boundary_redirect"):
        checks.append(
            {
                "name": "boundary_redirect_guidance",
                "passed": any(token in answer.lower() for token in ["verify", "check", "official", "dedicated live service", "确认", "核实", "实时服务", "官网"]),
            }
        )
    if intent == "attraction_explain":
        retrieval_name = _nested_str(metadata, "retrieval", "name")
        degraded = bool(metadata.get("degraded"))
        grounding = str(metadata.get("grounding") or metadata.get("retrieval_strategy") or "")
        grounded_signal = any(token in answer.lower() for token in ["history", "visitor tip", "highlight"]) or (
            bool(retrieval_name) and retrieval_name.lower() in answer.lower()
        )
        checks.append(
            {
                "name": "grounded_attraction_answer",
                "passed": grounded_signal or grounding == "model_knowledge" or degraded,
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



def _nested_value(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current



def _valid_navigation_legs(legs: object) -> bool:
    if not isinstance(legs, list) or not legs:
        return False
    for leg in legs:
        if not isinstance(leg, dict):
            return False
        if not leg.get("origin_name") or not leg.get("destination_name"):
            return False
    return True
