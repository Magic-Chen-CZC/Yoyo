from __future__ import annotations

import re
from typing import Any

import jieba

from yoyo.modules.qa.rule_assets import (
    ATTRACTION_EXPLAIN_KEYWORDS,
    ATTRACTION_NAMES,
    BOUNDARY_TOPIC_PATTERNS,
    DIRECT_PHRASES,
    JIEBA_CUSTOM_WORDS,
    LIVE_OPERATION_KEYWORDS,
    LIVE_TIME_KEYWORDS,
    NAVIGATION_ACTION_KEYWORDS,
    NAVIGATION_CONNECTOR_KEYWORDS,
    NAVIGATION_MODE_KEYWORDS,
    NAVIGATION_NEGATION_TARGET_KEYWORDS,
    NEGATION_OPERATOR_KEYWORDS,
    NORMALIZATION_REPLACEMENTS,
    ROUTE_EDIT_ACTION_KEYWORDS,
    ROUTE_EDIT_NEGATION_PATTERNS,
    ROUTE_EDIT_OBJECT_KEYWORDS,
    SOFT_ROUTE_EDIT_KEYWORDS,
    TRAFFIC_STATUS_KEYWORDS,
    TRANSLATION_ACTION_KEYWORDS,
    TRANSLATION_LANGUAGE_KEYWORDS,
    TRANSLATION_NEGATION_PATTERNS,
    TRANSLATION_OBJECT_KEYWORDS,
    TRIP_ARRANGEMENT_KEYWORDS,
    TRIP_PROGRESS_KEYWORDS,
    UNSUPPORTED_TRAVEL_PATTERNS,
    WEATHER_QUERY_KEYWORDS,
    WEATHER_TIME_KEYWORDS,
)

_SMALLTALK_FALLBACK_PATTERNS: tuple[str, ...] = (
    "你好",
    "您好",
    "哈喽",
    "hello",
    "hi",
    "hey",
    "早上好",
    "中午好",
    "晚上好",
    "谢谢",
    "多谢",
    "thank you",
    "thanks",
    "bye",
    "再见",
    "你是谁",
    "你能做什么",
    "人工客服",
    "智能导游",
    "导游助手",
    "怎么帮我",
    "能怎么帮我",
    "能不能陪我做讲解",
    "能力边界",
    "辛苦了",
    "暂时没有别的问题",
    "没有别的问题",
    "能力范围",
    "支持哪些功能",
    "只回答北京旅游问题",
    "会不会说中文",
    "负责北京游览问答",
    "打个招呼",
    "先打个招呼",
    "第一次用这个导游",
    "你会怎么回答问题",
    "会怎么回答问题",
    "简单说说你会怎么回答问题",
)
from yoyo.modules.qa.schemas import IntentRouterResult, QAIntent

_INTENT_PRIORITY: dict[QAIntent, int] = {
    "manual_route_edit_redirect": 8,
    "navigation_text": 7,
    "live_info": 6,
    "weather_info": 5,
    "translation": 4,
    "trip_assistant": 3,
    "attraction_explain": 2,
    "smalltalk": 1,
    "out_of_scope": 0,
}

_JIEBA_INITIALIZED = False

_BOUNDARY_NEGATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "traffic": (
        "不是问堵不堵",
        "不是问路况",
        "不是问交通拥堵",
        "不问堵不堵",
        "交通怎么走",
        "交通路线",
    ),
    "crowd": (
        "不是问人多不多",
        "不是问人多",
        "不是指人多",
        "不用管人多不多",
        "先不管人多不多",
        "不管人多不多",
        "不要查人多不多",
        "不问人多不多",
        "别查排队",
        "别查排队人数",
        "不查排队",
        "不查排队人数",
        "不是问排队",
        "不是问排队人数",
    ),
}

_UNSUPPORTED_NEGATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "transit_boundary": (
        "不坐地铁",
        "不要地铁",
        "不用地铁",
        "不是问地铁",
        "不坐公交",
    ),
    "restaurant_boundary": (
        "餐厅不用推荐",
        "不用推荐餐厅",
        "不是推荐餐厅",
        "不要推荐餐厅",
        "不是餐厅推荐",
    ),
    "air_quality_boundary": (
        "空气质量不是重点",
        "空气质量没关系",
        "不是问空气质量",
    ),
}

_CAPABILITY_PATTERNS: tuple[str, ...] = (
    "能力范围",
    "你能做什么",
    "能做什么",
    "支持哪些功能",
    "只回答北京旅游问题",
    "会不会说中文",
    "负责北京游览问答",
    "北京旅游助手",
    "人工客服",
    "智能导游",
    "导游助手",
    "怎么帮我",
    "能怎么帮我",
    "能不能陪我做讲解",
    "能力边界",
    "是不是在线",
    "收到消息了吗",
    "打个招呼",
    "先打个招呼",
    "第一次用这个导游",
    "你会怎么回答问题",
    "会怎么回答问题",
    "简单说说你会怎么回答问题",
)

_LIVE_NEGATION_PATTERNS: tuple[str, ...] = (
    "先别查开放时间",
    "别查开放时间",
    "不用继续查开放时间",
    "先不用继续查开放时间",
    "不继续查开放时间",
    "不是问开放时间",
    "不问开放时间",
    "先别查今天开不开",
    "先别查今天开不开门",
    "不是问今天开不开",
    "不是问开不开",
    "开不开先不查",
    "开不开我已经确认",
    "已经确认了",
    "先不查开放",
    "开放先不查",
    "先别查门票",
    "别管今天门票",
    "不是问门票",
)

def detect_intent(query: str, dialogue_history: list[dict[str, Any]] | None = None) -> str:
    return score_intent(query, dialogue_history)["intent"]


def score_intent(
    query: str,
    dialogue_history: list[dict[str, Any]] | None = None,
    *,
    raw_query: str | None = None,
) -> dict[str, Any]:
    normalized_query = _normalize_query(query)
    normalized_raw_query = _normalize_query(raw_query if isinstance(raw_query, str) else query)
    combined_text = _merge_text(normalized_query, normalized_raw_query)
    tokens = _tokenize(combined_text)
    history = dialogue_history or []
    last_intent = _last_intent(history)
    boundary_topic = _detect_boundary_topic(combined_text)
    unsupported_boundary = _detect_unsupported_boundary(combined_text)

    translation_direct = _direct_phrase_matches("translation", normalized_query, normalized_raw_query)
    route_direct = _direct_phrase_matches("manual_route_edit_redirect", normalized_query, normalized_raw_query)
    live_direct = _direct_phrase_matches("live_info", normalized_query, normalized_raw_query)
    weather_direct = _direct_phrase_matches("weather_info", normalized_query, normalized_raw_query)
    navigation_direct = _direct_phrase_matches("navigation_text", normalized_query, normalized_raw_query)
    attraction_direct = _direct_phrase_matches("attraction_explain", normalized_query, normalized_raw_query)
    trip_direct = _direct_phrase_matches("trip_assistant", normalized_query, normalized_raw_query)
    smalltalk_direct = _exact_phrase_matches(_SMALLTALK_FALLBACK_PATTERNS, normalized_query, normalized_raw_query)
    smalltalk_partial = _phrase_matches(_SMALLTALK_FALLBACK_PATTERNS, normalized_query, normalized_raw_query)

    translation_action = _keyword_matches(combined_text, tokens, TRANSLATION_ACTION_KEYWORDS)
    translation_language = _keyword_matches(combined_text, tokens, TRANSLATION_LANGUAGE_KEYWORDS)
    translation_object = _keyword_matches(combined_text, tokens, TRANSLATION_OBJECT_KEYWORDS)
    translation_negation = _keyword_matches(combined_text, tokens, TRANSLATION_NEGATION_PATTERNS)

    route_action = _keyword_matches(combined_text, tokens, ROUTE_EDIT_ACTION_KEYWORDS)
    route_object = _keyword_matches(combined_text, tokens, ROUTE_EDIT_OBJECT_KEYWORDS)
    route_soft = _keyword_matches(combined_text, tokens, SOFT_ROUTE_EDIT_KEYWORDS)
    route_negation = _keyword_matches(combined_text, tokens, ROUTE_EDIT_NEGATION_PATTERNS)

    live_time = _keyword_matches(combined_text, tokens, LIVE_TIME_KEYWORDS)
    live_operation = _keyword_matches(combined_text, tokens, LIVE_OPERATION_KEYWORDS)
    live_negation = _contains_any(combined_text, _LIVE_NEGATION_PATTERNS) or (
        "不用查" in combined_text and "开不开" in combined_text
    )
    weather_time = _keyword_matches(combined_text, tokens, WEATHER_TIME_KEYWORDS)
    weather_query = _keyword_matches(combined_text, tokens, WEATHER_QUERY_KEYWORDS)
    navigation_action = _keyword_matches(combined_text, tokens, NAVIGATION_ACTION_KEYWORDS)
    navigation_connector = _keyword_matches(combined_text, tokens, NAVIGATION_CONNECTOR_KEYWORDS)
    navigation_mode = _keyword_matches(combined_text, tokens, NAVIGATION_MODE_KEYWORDS)
    traffic_status = _keyword_matches(combined_text, tokens, TRAFFIC_STATUS_KEYWORDS)

    attraction_keywords = _keyword_matches(combined_text, tokens, ATTRACTION_EXPLAIN_KEYWORDS)
    attraction_names = _keyword_matches(combined_text, tokens, ATTRACTION_NAMES)

    trip_progress = _keyword_matches(combined_text, tokens, TRIP_PROGRESS_KEYWORDS)
    trip_arrangement = _keyword_matches(combined_text, tokens, TRIP_ARRANGEMENT_KEYWORDS)

    candidates: dict[QAIntent, float] = {
        "translation": 0.0,
        "live_info": 0.0,
        "weather_info": 0.0,
        "navigation_text": 0.0,
        "trip_assistant": 0.0,
        "attraction_explain": 0.0,
        "manual_route_edit_redirect": 0.0,
        "smalltalk": 0.0,
        "out_of_scope": 0.0,
    }
    signals: dict[QAIntent, list[str]] = {
        "translation": [],
        "live_info": [],
        "weather_info": [],
        "navigation_text": [],
        "trip_assistant": [],
        "attraction_explain": [],
        "manual_route_edit_redirect": [],
        "smalltalk": [],
        "out_of_scope": [],
    }

    if translation_direct:
        candidates["translation"] += 0.42
        signals["translation"].extend(translation_direct)
    if translation_action:
        candidates["translation"] += 0.18
        signals["translation"].append("translation_action_keyword")
    if translation_language:
        candidates["translation"] += 0.12
        signals["translation"].append("translation_language_keyword")
    if translation_object:
        candidates["translation"] += 0.08
        signals["translation"].append("translation_object_keyword")
    if translation_action and (translation_language or translation_object):
        candidates["translation"] += 0.16
        signals["translation"].append("translation_pattern_match")
    elif translation_language and translation_object and not translation_action:
        candidates["translation"] += 0.04
        signals["translation"].append("translation_context_only")
    if translation_negation:
        candidates["translation"] = max(0.0, candidates["translation"] - 0.7)
        signals["attraction_explain"].append("translation_negation")

    if route_direct:
        candidates["manual_route_edit_redirect"] += 0.42
        signals["manual_route_edit_redirect"].extend(route_direct)
    if route_action:
        candidates["manual_route_edit_redirect"] += 0.18
        signals["manual_route_edit_redirect"].append("route_edit_action_keyword")
        signals["manual_route_edit_redirect"].append("manual_route_edit_request")
    if route_object:
        candidates["manual_route_edit_redirect"] += 0.12
        signals["manual_route_edit_redirect"].append("route_edit_object_keyword")
    if route_action and attraction_names:
        candidates["manual_route_edit_redirect"] += 0.12
        signals["manual_route_edit_redirect"].append("route_edit_action_with_attraction")
    if "把" in combined_text and "换成" in combined_text and len(attraction_names) >= 2:
        candidates["manual_route_edit_redirect"] += 0.24
        signals["manual_route_edit_redirect"].append("route_replace_shape")
    if route_soft:
        candidates["manual_route_edit_redirect"] += 0.08
        signals["manual_route_edit_redirect"].append("route_edit_soft_keyword")
    if route_action and (route_object or route_soft):
        candidates["manual_route_edit_redirect"] += 0.16
        signals["manual_route_edit_redirect"].append("manual_route_edit_request")
    if "就把" in combined_text and route_action and attraction_names:
        candidates["manual_route_edit_redirect"] += 0.18
        signals["manual_route_edit_redirect"].append("conditional_route_edit_shape")
    if "把" in combined_text and "提前" in combined_text and attraction_names:
        candidates["manual_route_edit_redirect"] += 0.42
        signals["manual_route_edit_redirect"].append("route_reorder_advance_shape")
    if route_negation:
        candidates["manual_route_edit_redirect"] = max(0.0, candidates["manual_route_edit_redirect"] - 0.7)
        signals["trip_assistant"].append("route_edit_negation")
    if "开放到" in combined_text and candidates["manual_route_edit_redirect"] > 0:
        candidates["manual_route_edit_redirect"] = max(0.0, candidates["manual_route_edit_redirect"] - 0.36)
        signals["live_info"].append("open_until_phrase_not_route_edit")

    if live_direct:
        candidates["live_info"] += 0.4
        signals["live_info"].extend(live_direct)
    if live_time:
        candidates["live_info"] += 0.04
        signals["live_info"].append("live_time_keyword")
    if live_operation:
        candidates["live_info"] += 0.12
        signals["live_info"].append("live_operation_keyword")
    if live_time and live_operation:
        candidates["live_info"] += 0.18
        signals["live_info"].append("same_day_signal")
    if live_negation:
        candidates["live_info"] = max(0.0, candidates["live_info"] - 0.9)
        signals["live_info"].append("live_info_negation")
        if smalltalk_partial:
            candidates["smalltalk"] += 0.28
            signals["smalltalk"].append("smalltalk_with_negated_live_task")

    if weather_direct:
        candidates["weather_info"] += 0.4
        signals["weather_info"].extend(weather_direct)
    if weather_query:
        candidates["weather_info"] += 0.16
        signals["weather_info"].append("weather_query_keyword")
    if weather_time:
        candidates["weather_info"] += 0.08
        signals["weather_info"].append("weather_time_keyword")
    if weather_query and weather_time:
        candidates["weather_info"] += 0.16
        signals["weather_info"].append("weather_pattern_match")

    if navigation_direct:
        candidates["navigation_text"] += 0.42
        signals["navigation_text"].extend(navigation_direct)
    if navigation_action:
        candidates["navigation_text"] += 0.12
        signals["navigation_text"].append("navigation_action_keyword")
    has_explicit_path_shape = "从" in combined_text and ("到" in combined_text or "去" in combined_text)
    has_attraction_to_attraction_shape = bool(attraction_names) and "到" in combined_text
    if navigation_connector:
        candidates["navigation_text"] += 0.06
        signals["navigation_text"].append("navigation_connector_keyword")
    if navigation_mode:
        candidates["navigation_text"] += 0.08
        signals["navigation_text"].append("navigation_mode_keyword")
    has_embedded_destination_navigation = _looks_like_embedded_destination_navigation(combined_text)
    if navigation_action and has_explicit_path_shape:
        candidates["navigation_text"] += 0.2
        signals["navigation_text"].append("navigation_pattern_match")
    if navigation_action and has_embedded_destination_navigation:
        candidates["navigation_text"] += 0.28
        signals["navigation_text"].append("embedded_destination_navigation_pattern")
    if navigation_action and has_attraction_to_attraction_shape:
        candidates["navigation_text"] += 0.18
        signals["navigation_text"].append("attraction_to_attraction_navigation_pattern")
    if navigation_action and _contains_any(combined_text, ("附近", "周边", "交通怎么走", "交通路线")):
        candidates["navigation_text"] += 0.14
        signals["navigation_text"].append("nearby_navigation_pattern")
    if _has_negated_keyword(
        combined_text,
        negation_keywords=NEGATION_OPERATOR_KEYWORDS,
        target_keywords=NAVIGATION_NEGATION_TARGET_KEYWORDS,
    ):
        candidates["navigation_text"] = max(0.0, candidates["navigation_text"] - 0.7)
        signals["trip_assistant"].append("navigation_negation")

    if attraction_direct:
        candidates["attraction_explain"] += 0.3
        signals["attraction_explain"].extend(attraction_direct)
    if attraction_keywords:
        candidates["attraction_explain"] += 0.12
        signals["attraction_explain"].append("explain_keyword")
    if attraction_names:
        candidates["attraction_explain"] += 0.14
        signals["attraction_explain"].append("explicit_attraction_signal")
    if attraction_keywords and attraction_names:
        candidates["attraction_explain"] += 0.16
        signals["attraction_explain"].append("attraction_pattern_match")

    if trip_direct:
        candidates["trip_assistant"] += 0.42
        signals["trip_assistant"].extend(trip_direct)
    if trip_progress:
        candidates["trip_assistant"] += 0.1
        signals["trip_assistant"].append("trip_progress_keyword")
    if trip_arrangement:
        candidates["trip_assistant"] += 0.08
        signals["trip_assistant"].append("trip_arrangement_keyword")
    if trip_progress and trip_arrangement:
        candidates["trip_assistant"] += 0.22
        signals["trip_assistant"].append("next_after_signal")

    if smalltalk_direct:
        candidates["smalltalk"] += 0.52
        signals["smalltalk"].extend(smalltalk_direct)
    elif smalltalk_partial:
        candidates["smalltalk"] += 0.18
        signals["smalltalk"].extend(smalltalk_partial)
        signals["smalltalk"].append("smalltalk_partial_phrase")
    elif _looks_like_smalltalk_only(combined_text):
        candidates["smalltalk"] += 0.32
        signals["smalltalk"].append("smalltalk_fallback_pattern")
    has_capability_query = _contains_any(combined_text, _CAPABILITY_PATTERNS)
    if has_capability_query:
        candidates["smalltalk"] += 0.42
        signals["smalltalk"].append("capability_or_identity_query")

    if boundary_topic is not None:
        candidates["out_of_scope"] += 0.6
        signals["out_of_scope"].append("boundary_live_topic_signal")
        if boundary_topic == "traffic" and navigation_action and navigation_connector and not traffic_status:
            candidates["navigation_text"] += 0.16
            signals["navigation_text"].append("navigation_priority_over_traffic_boundary")

    has_transit_navigation_request = (
        unsupported_boundary == "transit_boundary"
        and (navigation_action or has_explicit_path_shape or has_embedded_destination_navigation)
        and navigation_connector
    )
    if unsupported_boundary is not None and not has_transit_navigation_request:
        candidates["out_of_scope"] += 0.52
        signals["out_of_scope"].append(unsupported_boundary)
        if unsupported_boundary == "transit_boundary" and _contains_any(
            combined_text,
            ("不是问步行路线", "不是问步行", "不是问路线", "我不是问步行路线", "不是要步行路线"),
        ):
            candidates["out_of_scope"] += 0.24
            candidates["navigation_text"] = max(0.0, candidates["navigation_text"] - 0.64)
            signals["out_of_scope"].append("transit_query_negates_walking_navigation")
        if unsupported_boundary == "parking_boundary" and _contains_any(combined_text, ("停车场", "车位", "停车")):
            candidates["out_of_scope"] += 0.24
            candidates["navigation_text"] = max(0.0, candidates["navigation_text"] - 0.44)
            signals["out_of_scope"].append("parking_boundary_priority")
    elif has_transit_navigation_request:
        candidates["navigation_text"] += 0.2
        signals["navigation_text"].append("transit_navigation_supported")

    has_translation_live_conflict = candidates["translation"] > 0 and candidates["live_info"] > 0
    has_live_weather_conflict = candidates["live_info"] > 0 and candidates["weather_info"] > 0 and bool(live_operation)
    has_navigation_trip_conflict = candidates["navigation_text"] >= 0.18 and candidates["trip_assistant"] >= 0.18
    has_navigation_attraction_conflict = (
        candidates["navigation_text"] >= 0.18 and candidates["attraction_explain"] > 0
    )
    if has_navigation_attraction_conflict:
        signals["navigation_text"].append("navigation_attraction_conflict")
        signals["attraction_explain"].append("navigation_attraction_conflict")
        if _contains_any(combined_text, ("文字步骤", "分两段", "分段说")):
            candidates["navigation_text"] += 0.16
            signals["navigation_text"].append("navigation_steps_priority_over_attraction")
        if _contains_any(combined_text, ("按路线说", "按路线讲", "按路线")) and _contains_any(
            combined_text,
            ("不展开历史", "不讲历史", "不展开讲", "先按路线"),
        ):
            candidates["navigation_text"] += 0.14
            candidates["attraction_explain"] = max(0.0, candidates["attraction_explain"] - 0.04)
            signals["navigation_text"].append("route_first_phrase_priority")

    has_weather_attraction_conflict = candidates["weather_info"] > 0 and candidates["attraction_explain"] > 0
    if has_weather_attraction_conflict:
        signals["weather_info"].append("weather_attraction_conflict")
        signals["attraction_explain"].append("weather_attraction_conflict")
        if _contains_any(
            combined_text,
            ("现在问的是今天温度", "问的是今天温度", "今天温度", "温度大概多少", "今天适合去", "适合去吗"),
        ):
            candidates["weather_info"] += 0.24
            candidates["attraction_explain"] = max(0.0, candidates["attraction_explain"] - 0.08)
            signals["weather_info"].append("weather_focus_phrase_priority")

    if candidates["translation"] > 0 and candidates["attraction_explain"] > 0:
        if translation_action:
            candidates["translation"] += 0.12
            signals["translation"].append("translation_priority_over_attraction")
        else:
            candidates["attraction_explain"] += 0.06
            signals["attraction_explain"].append("attraction_priority_without_translation_action")

    if has_translation_live_conflict:
        candidates["translation"] += 0.08
        signals["translation"].append("translation_live_conflict")
        signals["live_info"].append("translation_live_conflict")
        if translation_action:
            candidates["translation"] += 0.1
            signals["translation"].append("translation_priority_over_live_info")
        if live_time and live_operation:
            candidates["live_info"] += 0.08
            signals["live_info"].append("live_info_priority_over_translation")

    if candidates["manual_route_edit_redirect"] > 0 and candidates["trip_assistant"] > 0:
        if route_action:
            candidates["manual_route_edit_redirect"] += 0.12
            signals["manual_route_edit_redirect"].append("route_edit_priority_over_trip_assistant")
        else:
            candidates["trip_assistant"] += 0.04
            signals["trip_assistant"].append("trip_assistant_priority_without_route_action")

    if has_live_weather_conflict:
        signals["live_info"].append("live_weather_conflict")
        signals["weather_info"].append("live_weather_conflict")
        if _contains_any(combined_text, ("现在问的是今天温度", "问的是今天温度", "今天温度", "温度大概多少")):
            candidates["weather_info"] += 0.18
            candidates["live_info"] = max(0.0, candidates["live_info"] - 0.08)
            signals["weather_info"].append("weather_focus_phrase_priority")
        if live_operation:
            candidates["live_info"] += 0.06
            signals["live_info"].append("live_info_priority_over_weather")
        if weather_query:
            candidates["weather_info"] += 0.08
            signals["weather_info"].append("weather_priority_over_live_info")

    if has_navigation_trip_conflict:
        signals["navigation_text"].append("navigation_trip_conflict")
        signals["trip_assistant"].append("navigation_trip_conflict")
        has_followup_navigation_phrase = _contains_any(
            combined_text,
            ("接下来怎么走", "接下来怎么去", "下一站怎么走", "下一站怎么去", "往哪边走", "应该往哪边走"),
        )
        has_current_stop_status_phrase = _contains_any(combined_text, ("哪一站", "当前站", "当前在哪", "现在到哪"))
        if route_negation and navigation_action:
            candidates["navigation_text"] += 0.16
            candidates["trip_assistant"] = max(0.0, candidates["trip_assistant"] - 0.1)
            signals["navigation_text"].append("navigation_priority_with_route_edit_negation")
        elif route_negation and trip_progress:
            candidates["trip_assistant"] += 0.16
            candidates["navigation_text"] = max(0.0, candidates["navigation_text"] - 0.1)
            signals["trip_assistant"].append("trip_assistant_priority_with_route_negation")
        elif has_embedded_destination_navigation:
            candidates["navigation_text"] += 0.14
            candidates["trip_assistant"] = max(0.0, candidates["trip_assistant"] - 0.1)
            signals["navigation_text"].append("embedded_destination_priority_over_trip")
        elif _contains_any(combined_text, ("现在问的是下一站怎么走", "下一站怎么走")) and _contains_any(
            combined_text,
            ("知道了", "已知道", "我知道了"),
        ):
            candidates["navigation_text"] += 0.36
            candidates["trip_assistant"] = max(0.0, candidates["trip_assistant"] - 0.18)
            signals["navigation_text"].append("navigation_focus_after_trip_known")
        elif has_current_stop_status_phrase and trip_progress:
            candidates["trip_assistant"] += 0.12
            candidates["navigation_text"] = max(0.0, candidates["navigation_text"] - 0.06)
            signals["trip_assistant"].append("current_stop_status_phrase_priority")
        elif has_followup_navigation_phrase:
            candidates["navigation_text"] += 0.1
            signals["navigation_text"].append("followup_navigation_phrase_priority")
        elif navigation_connector and navigation_action:
            candidates["navigation_text"] += 0.1
            signals["navigation_text"].append("navigation_priority_over_trip_assistant")
        elif trip_progress:
            candidates["trip_assistant"] += 0.06
            signals["trip_assistant"].append("trip_assistant_priority_over_navigation")

    has_live_attraction_conflict = (
        candidates["live_info"] > 0
        and candidates["attraction_explain"] > 0
        and (bool(live_direct) or bool(live_operation))
    )
    if has_live_attraction_conflict:
        signals["live_info"].append("live_attraction_conflict")
        signals["attraction_explain"].append("live_attraction_conflict")
        if live_time and live_operation:
            candidates["live_info"] += 0.08
            signals["live_info"].append("live_info_priority_over_attraction")
        else:
            candidates["attraction_explain"] += 0.08
            signals["attraction_explain"].append("attraction_priority_without_same_day_signal")

    if translation_negation and candidates["attraction_explain"] > 0:
        candidates["attraction_explain"] += 0.12
        signals["attraction_explain"].append("attraction_priority_with_translation_negation")

    best_intent = _pick_best_intent(candidates)
    best_score = round(candidates[best_intent], 3)
    runner_up_intent, runner_up_score = _runner_up(candidates, best_intent)
    margin = round(max(0.0, best_score - runner_up_score), 3)
    confidence = round(min(0.99, max(0.12, 0.42 + best_score * 0.28 + margin * 0.45)), 3)
    fallback_reason = _fallback_reason(
        combined_text=combined_text,
        best_intent=best_intent,
        best_score=best_score,
        runner_up_intent=runner_up_intent,
        margin=margin,
        boundary_topic=boundary_topic,
        unsupported_boundary=unsupported_boundary,
        has_live_attraction_conflict=has_live_attraction_conflict,
        has_translation_live_conflict=has_translation_live_conflict,
        has_live_weather_conflict=has_live_weather_conflict,
        has_navigation_trip_conflict=has_navigation_trip_conflict,
        has_navigation_attraction_conflict=has_navigation_attraction_conflict,
        has_capability_query=has_capability_query,
        has_translation_attraction_conflict=candidates["translation"] > 0 and candidates["attraction_explain"] > 0,
    )
    needs_fallback = fallback_reason is not None
    out_of_scope_subtype = _infer_out_of_scope_subtype(best_intent, boundary_topic, best_score, margin)

    result = IntentRouterResult(
        intent=best_intent,
        confidence=confidence,
        margin=margin,
        needs_fallback=needs_fallback,
        fallback_reason=fallback_reason,
        signals=signals[best_intent],
        candidates={key: round(value, 3) for key, value in candidates.items()},
        runner_up_intent=runner_up_intent,
        last_intent=last_intent,
        boundary_topic=boundary_topic,
        out_of_scope_subtype=out_of_scope_subtype,
    )
    return result.model_dump()


def _normalize_query(text: str) -> str:
    normalized = " ".join(text.strip().split()).lower()
    for old, new in NORMALIZATION_REPLACEMENTS:
        normalized = normalized.replace(old, new)
    return normalized


def _tokenize(text: str) -> list[str]:
    _initialize_jieba()
    return [token.strip().lower() for token in jieba.lcut(text) if token.strip()]


def _initialize_jieba() -> None:
    global _JIEBA_INITIALIZED
    if _JIEBA_INITIALIZED:
        return
    for word in JIEBA_CUSTOM_WORDS:
        jieba.add_word(word)
    _JIEBA_INITIALIZED = True


def _merge_text(*texts: str) -> str:
    merged = []
    for text in texts:
        if text and text not in merged:
            merged.append(text)
    return " ".join(merged)


def _direct_phrase_matches(intent: str, *texts: str) -> list[str]:
    return _merge_matches(*[_matched_patterns(text, DIRECT_PHRASES.get(intent, ())) for text in texts])


def _keyword_matches(text: str, tokens: list[str], keywords: tuple[str, ...]) -> list[str]:
    token_set = set(tokens)
    matches: list[str] = []
    for keyword in keywords:
        if keyword in text or keyword in token_set:
            matches.append(keyword)
    return matches


def _matched_patterns(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if pattern in text]


def _phrase_matches(patterns: tuple[str, ...], *texts: str) -> list[str]:
    return _merge_matches(*[_matched_phrase_patterns(text, patterns) for text in texts])


def _exact_phrase_matches(patterns: tuple[str, ...], *texts: str) -> list[str]:
    return _merge_matches(*[_matched_exact_patterns(text, patterns) for text in texts])


def _matched_phrase_patterns(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if _contains_phrase(text, pattern)]


def _matched_exact_patterns(text: str, patterns: tuple[str, ...]) -> list[str]:
    stripped = text.strip().lower().rstrip("。！？!?~,.，")
    return [pattern for pattern in patterns if stripped == pattern]


def _merge_matches(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for item in group:
            if item not in merged:
                merged.append(item)
    return merged


def _last_intent(dialogue_history: list[dict[str, Any]]) -> QAIntent | None:
    for item in reversed(dialogue_history):
        intent = item.get("intent")
        if intent in _INTENT_PRIORITY:
            return intent
    return None


def _pick_best_intent(candidates: dict[QAIntent, float]) -> QAIntent:
    if max(candidates.values(), default=0.0) <= 0.0:
        return "out_of_scope"
    return max(
        candidates,
        key=lambda intent: (
            candidates[intent],
            _INTENT_PRIORITY[intent],
        ),
    )


def _runner_up(candidates: dict[QAIntent, float], best_intent: QAIntent) -> tuple[QAIntent | None, float]:
    remaining = sorted(
        ((intent, score) for intent, score in candidates.items() if intent != best_intent),
        key=lambda item: (item[1], _INTENT_PRIORITY[item[0]]),
        reverse=True,
    )
    if not remaining:
        return None, 0.0
    return remaining[0]


def _looks_like_smalltalk_only(text: str) -> bool:
    stripped = text.strip().lower().rstrip("。！？!?~,.，")
    return stripped in _SMALLTALK_FALLBACK_PATTERNS


def _contains_phrase(text: str, pattern: str) -> bool:
    if not pattern:
        return False
    if pattern.isascii():
        return re.search(rf"(?<![a-z]){re.escape(pattern)}(?![a-z])", text) is not None
    return pattern in text


def _detect_boundary_topic(text: str) -> str | None:
    for topic, patterns in BOUNDARY_TOPIC_PATTERNS.items():
        if any(pattern in text for pattern in patterns) and not _contains_any(
            text,
            _BOUNDARY_NEGATION_PATTERNS.get(topic, ()),
        ):
            return topic
    return None


def _detect_unsupported_boundary(text: str) -> str | None:
    for boundary_name, patterns in UNSUPPORTED_TRAVEL_PATTERNS.items():
        if any(pattern in text for pattern in patterns) and not _contains_any(
            text,
            _UNSUPPORTED_NEGATION_PATTERNS.get(boundary_name, ()),
        ):
            return boundary_name
    return None


def _fallback_reason(
    *,
    combined_text: str,
    best_intent: QAIntent,
    best_score: float,
    runner_up_intent: QAIntent | None,
    margin: float,
    boundary_topic: str | None,
    unsupported_boundary: str | None,
    has_live_attraction_conflict: bool,
    has_translation_live_conflict: bool,
    has_live_weather_conflict: bool,
    has_navigation_trip_conflict: bool,
    has_navigation_attraction_conflict: bool,
    has_capability_query: bool,
    has_translation_attraction_conflict: bool,
) -> str | None:
    if boundary_topic is not None and best_intent == "out_of_scope":
        return "boundary_topic_conflict"
    if best_intent == "navigation_text" and navigation_text_is_strong(combined_text, best_score, margin):
        return None
    if has_live_attraction_conflict:
        return "live_vs_attraction_conflict"
    if has_translation_live_conflict:
        return "translation_live_conflict"
    if has_translation_attraction_conflict and (margin < 0.2 or _contains_any(combined_text, TRANSLATION_NEGATION_PATTERNS)):
        return "translation_vs_attraction_conflict"
    if has_live_weather_conflict:
        return "live_vs_weather_conflict"
    if has_navigation_trip_conflict:
        if best_intent == "trip_assistant" and _contains_any(combined_text, ROUTE_EDIT_NEGATION_PATTERNS):
            return None
        if best_intent == "trip_assistant" and _contains_any(combined_text, ("哪一站", "当前站", "当前在哪", "现在到哪")) and best_score >= 0.56 and margin >= 0.2:
            return None
        if best_intent == "navigation_text" and _contains_any(combined_text, ("接下来怎么走", "接下来怎么去", "下一站怎么走", "下一站怎么去")) and best_score >= 0.56 and margin >= 0.2:
            return None
        return "navigation_vs_trip_conflict"
    if has_navigation_attraction_conflict and (
        margin < 0.18 or _contains_any(combined_text, ("按路线讲", "按路线说", "路线说", "顺路"))
    ):
        return "navigation_vs_attraction_conflict"
    if has_capability_query and best_intent != "smalltalk":
        return "smalltalk_capability_conflict"
    if best_intent == "out_of_scope" and unsupported_boundary is not None and best_score >= 0.6 and margin >= 0.2:
        return None
    if best_intent == "manual_route_edit_redirect":
        if route_edit_is_strong(combined_text, best_score, margin):
            return None
        return "low_top_score"
    if best_intent == "translation" and best_score >= 0.66 and margin >= 0.18:
        return None
    if best_intent == "live_info" and _contains_any(combined_text, LIVE_TIME_KEYWORDS) and _contains_any(combined_text, LIVE_OPERATION_KEYWORDS) and best_score >= 0.54 and margin >= 0.14:
        return None
    if best_intent == "weather_info" and _contains_any(combined_text, WEATHER_QUERY_KEYWORDS) and best_score >= 0.44 and margin >= 0.12:
        return None
    if best_intent == "attraction_explain" and _contains_any(combined_text, ATTRACTION_EXPLAIN_KEYWORDS) and _contains_any(combined_text, ATTRACTION_NAMES) and best_score >= 0.5 and margin >= 0.14:
        return None
    if best_intent == "trip_assistant" and trip_assistant_is_strong(combined_text, best_score, margin):
        return None
    if (
        best_intent == "trip_assistant"
        and _contains_any(combined_text, ROUTE_EDIT_NEGATION_PATTERNS)
        and _contains_any(combined_text, TRIP_PROGRESS_KEYWORDS)
        and _contains_any(combined_text, TRIP_ARRANGEMENT_KEYWORDS)
        and best_score >= 0.36
    ):
        return None
    if best_intent == "smalltalk":
        if has_capability_query and best_score >= 0.42:
            return None
        if _looks_like_smalltalk_only(combined_text) and best_score >= 0.3:
            return None
        if _contains_any(combined_text, _SMALLTALK_FALLBACK_PATTERNS) and _contains_any(
            combined_text,
            ("不用继续查", "先不用继续查", "不用查", "先别查", "别查", "不是问"),
        ):
            return None
        return "smalltalk_with_extra_content"
    if best_score < 0.18:
        return "low_top_score"
    if margin < 0.08:
        return "small_margin"
    if runner_up_intent in {"live_info", "attraction_explain"} and best_intent in {"live_info", "attraction_explain"}:
        return "live_vs_attraction_conflict"
    if runner_up_intent in {"live_info", "weather_info"} and best_intent in {"live_info", "weather_info"}:
        return "live_vs_weather_conflict"
    if runner_up_intent in {"trip_assistant", "manual_route_edit_redirect"} and best_intent in {"trip_assistant", "manual_route_edit_redirect"}:
        return "trip_vs_edit_conflict"
    if runner_up_intent in {"trip_assistant", "navigation_text"} and best_intent in {"trip_assistant", "navigation_text"}:
        return "navigation_vs_trip_conflict"
    return None


def _infer_out_of_scope_subtype(
    best_intent: QAIntent,
    boundary_topic: str | None,
    best_score: float,
    margin: float,
) -> str | None:
    if best_intent != "out_of_scope":
        return None
    if boundary_topic == "traffic":
        return "traffic_boundary"
    if boundary_topic == "crowd":
        return "crowd_boundary"
    if best_score < 0.18:
        return "low_confidence_unclassified"
    if margin < 0.08:
        return "weak_travel_adjacent_unclassified"
    return "general_out_of_scope"


def route_edit_is_strong(text: str, best_score: float, margin: float) -> bool:
    if _contains_any(text, ROUTE_EDIT_NEGATION_PATTERNS):
        return False
    return (
        (
            _contains_any(text, ROUTE_EDIT_OBJECT_KEYWORDS)
            or _contains_any(text, SOFT_ROUTE_EDIT_KEYWORDS)
            or _contains_any(text, ATTRACTION_NAMES)
        )
        and _contains_any(text, ROUTE_EDIT_ACTION_KEYWORDS)
        and best_score >= 0.28
        and margin >= 0.1
    )


def trip_assistant_is_strong(text: str, best_score: float, margin: float) -> bool:
    return (
        _contains_any(text, TRIP_PROGRESS_KEYWORDS)
        and _contains_any(text, TRIP_ARRANGEMENT_KEYWORDS)
        and best_score >= 0.4
        and margin >= 0.14
    )


def navigation_text_is_strong(text: str, best_score: float, margin: float) -> bool:
    has_navigation_phrase = _contains_any(text, NAVIGATION_ACTION_KEYWORDS)
    has_explicit_route = "从" in text and ("到" in text or "去" in text)
    has_destination_only = (text.startswith("去") or text.startswith("到")) and has_navigation_phrase
    has_next_stop_navigation = _contains_any(text, ("下一站怎么去", "下一站怎么走", "接下来怎么去", "接下来怎么走"))
    has_multi_leg_navigation = _contains_any(text, ("再到", "再去", "然后到", "然后去")) and has_navigation_phrase
    has_embedded_destination_navigation = _looks_like_embedded_destination_navigation(text)
    if has_next_stop_navigation and has_navigation_phrase and best_score >= 0.42:
        return True
    return (
        has_explicit_route
        or has_destination_only
        or has_next_stop_navigation
        or has_multi_leg_navigation
        or has_embedded_destination_navigation
        or (_contains_any(text, NAVIGATION_MODE_KEYWORDS) and has_navigation_phrase)
    ) and best_score >= 0.42 and margin >= 0.12


def _looks_like_embedded_destination_navigation(text: str) -> bool:
    if not _contains_any(text, NAVIGATION_ACTION_KEYWORDS):
        return False
    if _contains_any(text, ("去哪里", "去哪", "到哪里", "到哪")) and not _contains_any(
        text,
        ("怎么走", "怎么去", "导航", "路线", "文字步骤", "分段路线"),
    ):
        return False
    markers = (
        "想去",
        "我要去",
        "我想去",
        "准备去",
        "打算去",
        "等会去",
        "一会去",
        "接着去",
        "然后去",
        "前往",
        "导航到",
        "下面到",
        "到",
        "去",
    )
    return any(marker in text for marker in markers)


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _has_negated_keyword(
    text: str,
    *,
    negation_keywords: tuple[str, ...],
    target_keywords: tuple[str, ...],
    max_gap: int = 4,
) -> bool:
    for negation in negation_keywords:
        if not negation:
            continue
        for target in target_keywords:
            if not target:
                continue
            negation_pattern = re.escape(negation)
            if negation == "别":
                negation_pattern = rf"{negation_pattern}(?!的)"
            if re.search(rf"{negation_pattern}.{{0,{max_gap}}}{re.escape(target)}", text):
                return True
    return False
