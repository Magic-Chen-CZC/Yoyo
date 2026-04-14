# planner handoff 的作用是：把“用户自然语言里的改路线意图”整理成结构化数据。
# 当前阶段保持契约稳定，但扩展 operation、target 和 constraints 的解析覆盖。
from yoyo.modules.qa.schemas import PlannerHandoffPayload


_KNOWN_TARGETS = [
    "Tiananmen Square",
    "Forbidden City",
    "Jingshan Park",
    "Temple of Heaven",
    "Summer Palace",
]


def build_planner_handoff(query: str, available_stops: list[str] | None = None) -> PlannerHandoffPayload:
    lowered = query.lower()

    if "replace" in lowered or "swap" in lowered or "换一个" in lowered:
        operation = "replace_stop"
    elif "remove" in lowered or "delete" in lowered or "删掉" in lowered:
        operation = "remove_stop"
    elif "reorder" in lowered or "move" in lowered or "调整顺序" in lowered:
        operation = "reorder_stops"
    elif "shorten" in lowered or "fewer" in lowered or "shorter" in lowered or "更轻松" in lowered:
        operation = "shorten_route"
    else:
        operation = "update_route"

    target = _extract_target(query, available_stops or [])
    constraints: dict[str, str] = {}
    if "scenic" in lowered or "view" in lowered or "photo" in lowered:
        constraints["theme"] = "scenic"
    elif "history" in lowered or "historical" in lowered or "culture" in lowered:
        constraints["theme"] = "historical"
    if "child" in lowered or "family" in lowered or "kid" in lowered:
        constraints["audience"] = "family"
    if "fewer stairs" in lowered or "less tiring" in lowered or "easier" in lowered or "less walking" in lowered:
        constraints["walking"] = "lighter"
    if "faster" in lowered or "quick" in lowered:
        constraints["pace"] = "faster"
    elif "slower" in lowered or "relaxed" in lowered or "easy pace" in lowered:
        constraints["pace"] = "slower"
    if "avoid crowds" in lowered or "less crowded" in lowered:
        constraints["crowd"] = "avoid_crowds"
    if "half day" in lowered or "shorter" in lowered or "less time" in lowered:
        constraints["time_budget"] = "shorter"
    if "earlier" in lowered or "first" in lowered:
        constraints["position_hint"] = "earlier"
    elif "later" in lowered or "last" in lowered or "after" in lowered:
        constraints["position_hint"] = "later"

    return PlannerHandoffPayload(
        operation=operation,
        target=target,
        constraints=constraints,
    )



def _extract_target(query: str, available_stops: list[str]) -> str | None:
    lowered = query.lower()
    for stop in available_stops:
        if stop.lower() in lowered:
            return stop
    for target in _KNOWN_TARGETS:
        if target.lower() in lowered:
            return target
    return None
