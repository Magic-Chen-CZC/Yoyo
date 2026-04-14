# intent router 负责给问题分流。
# 当前阶段采用：规则优先 + 置信度 + 冲突处理，并保留未来轻量语义 fallback 的扩展空间。
from __future__ import annotations

from typing import Any


_TRANSLATION_HINTS = ["translate", "translation", "rewrite", "say this in english", "翻译", "怎么说"]
_LIVE_INFO_HINTS = [
    "weather",
    "open",
    "opening hours",
    "hours",
    "ticket",
    "today",
    "currently",
    "queue",
    "closed",
    "closure",
    "预约",
    "开放",
    "门票",
]
_PLANNER_HINTS = [
    "replace",
    "swap",
    "remove",
    "delete",
    "change route",
    "reorder",
    "move",
    "shorten",
    "fewer",
    "less walking",
    "easier route",
    "换一个",
    "删掉",
    "调整路线",
]
_TRIP_HINTS = [
    "next stop",
    "next",
    "route",
    "itinerary",
    "where should",
    "how long",
    "after this",
    "after that",
    "what should i do next",
    "下一站",
    "接下来",
]
_ATTRACTION_HINTS = [
    "tell me more",
    "explain",
    "history",
    "why is it important",
    "介绍",
    "讲讲",
]
_FOLLOW_UP_HINTS = ["what about", "that one", "it", "tell me more", "more about it", "and next", "那这个", "它"]

_INTENT_PRIORITY = {
    "planner_handoff": 5,
    "live_info": 4,
    "translation": 3,
    "trip_assistant": 2,
    "attraction_explain": 1,
}



def detect_intent(query: str, dialogue_history: list[dict[str, Any]] | None = None) -> str:
    return score_intent(query, dialogue_history)["intent"]



def score_intent(query: str, dialogue_history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    lowered = query.lower().strip()
    history = dialogue_history or []
    last_intent = _last_intent(history)

    candidates: dict[str, float] = {
        "translation": _score_from_patterns(lowered, _TRANSLATION_HINTS, 0.34),
        "live_info": _score_from_patterns(lowered, _LIVE_INFO_HINTS, 0.28),
        "planner_handoff": _score_from_patterns(lowered, _PLANNER_HINTS, 0.32),
        "trip_assistant": _score_from_patterns(lowered, _TRIP_HINTS, 0.18),
        "attraction_explain": _score_from_patterns(lowered, _ATTRACTION_HINTS, 0.16),
    }

    signals: dict[str, list[str]] = {
        "translation": _matched_patterns(lowered, _TRANSLATION_HINTS),
        "live_info": _matched_patterns(lowered, _LIVE_INFO_HINTS),
        "planner_handoff": _matched_patterns(lowered, _PLANNER_HINTS),
        "trip_assistant": _matched_patterns(lowered, _TRIP_HINTS),
        "attraction_explain": _matched_patterns(lowered, _ATTRACTION_HINTS),
    }

    if _matches_any(lowered, _FOLLOW_UP_HINTS) and last_intent in {"attraction_explain", "trip_assistant", "planner_handoff"}:
        candidates[last_intent] += 0.18
        signals[last_intent].append("follow_up_from_history")

    if any(token in lowered for token in ["next", "after", "下一站"]):
        candidates["trip_assistant"] += 0.15
        signals["trip_assistant"].append("next_after_signal")

    if any(token in lowered for token in ["today", "currently", "open", "hours", "ticket", "weather"]):
        candidates["live_info"] += 0.16
        signals["live_info"].append("same_day_signal")

    if any(token in lowered for token in ["replace", "swap", "remove", "shorten", "less walking", "easier route", "换一个", "删掉"]):
        candidates["planner_handoff"] += 0.18
        signals["planner_handoff"].append("route_edit_signal")

    if any(token in lowered for token in ["attraction", "景点"]) and not any(
        token in lowered for token in ["replace", "swap", "remove", "delete", "reorder", "move", "shorten", "换一个", "删掉"]
    ):
        candidates["attraction_explain"] += 0.14
        signals["attraction_explain"].append("explicit_attraction_signal")

    if candidates["planner_handoff"] > 0 and candidates["trip_assistant"] > 0:
        candidates["planner_handoff"] += 0.14
        signals["planner_handoff"].append("route_edit_priority_over_trip")

    if candidates["live_info"] > 0 and candidates["attraction_explain"] > 0:
        candidates["live_info"] += 0.08
        signals["live_info"].append("live_info_priority_over_attraction")

    if any(token in lowered for token in ["tell me more", "history", "why is it important", "介绍", "讲讲"]):
        candidates["attraction_explain"] += 0.12
        signals["attraction_explain"].append("explain_signal")

    best_intent = _pick_best_intent(candidates)
    best_score = round(candidates[best_intent], 3)
    runner_up_score = _runner_up_score(candidates, best_intent)
    confidence = round(min(0.99, max(0.2, best_score - runner_up_score + 0.45)), 3)

    return {
        "intent": best_intent,
        "confidence": confidence,
        "signals": signals[best_intent],
        "candidates": {key: round(value, 3) for key, value in candidates.items()},
        "last_intent": last_intent,
    }



def _score_from_patterns(text: str, patterns: list[str], weight: float) -> float:
    return len(_matched_patterns(text, patterns)) * weight



def _matched_patterns(text: str, patterns: list[str]) -> list[str]:
    return [pattern for pattern in patterns if pattern in text]



def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)



def _last_intent(dialogue_history: list[dict[str, Any]]) -> str | None:
    for item in reversed(dialogue_history):
        intent = item.get("intent")
        if isinstance(intent, str) and intent:
            return intent
    return None



def _pick_best_intent(candidates: dict[str, float]) -> str:
    return max(
        candidates,
        key=lambda intent: (
            candidates[intent],
            _INTENT_PRIORITY[intent],
        ),
    )



def _runner_up_score(candidates: dict[str, float], best_intent: str) -> float:
    remaining = [score for intent, score in candidates.items() if intent != best_intent]
    return max(remaining) if remaining else 0.0
