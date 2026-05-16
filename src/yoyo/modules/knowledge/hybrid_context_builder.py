from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.modules.knowledge.attraction_retriever import get_attraction_context
from yoyo.modules.knowledge.fallback_router import should_use_rag_fallback
from yoyo.modules.knowledge.live_retriever import get_live_info_context
from yoyo.modules.knowledge.navigation_retriever import get_navigation_context
from yoyo.modules.knowledge.place_resolver import (
    is_current_location_reference,
    make_gps_navigation_place,
    navigation_candidate_places,
    resolve_navigation_place,
)
from yoyo.modules.knowledge.profile_retriever import get_profile_context
from yoyo.modules.knowledge.prompt_projection import project_attraction_for_prompt, project_profile_for_prompt
from yoyo.modules.knowledge.rag_retriever import get_rag_context
from yoyo.modules.knowledge.schemas import HybridContext, NavigationSlotPayload
from yoyo.modules.knowledge.weather_retriever import get_weather_context
from yoyo.modules.qa.router_fallback import resolve_navigation_slot_fallback
from yoyo.modules.qa.rule_assets import NAVIGATION_MULTI_STOP_PATTERNS, NAVIGATION_NEXT_STOP_PATTERNS
from yoyo.modules.qa.schemas import NavigationSlotResult


_CITY_CODE_TO_WEATHER_LOCATION = {
    "beijing": "Beijing",
}

_DEFAULT_TRANSIT_THRESHOLD_METERS = 3000


async def build_hybrid_context(
    *,
    intent: str,
    query: str,
    attraction_name: str | None,
    user_id: str | None,
    session_context: dict,
    dialogue_history: list[dict],
    session: AsyncSession | None = None,
) -> HybridContext:
    started_at = perf_counter()
    timings: dict[str, int | str | bool | None] = {}

    attraction = await _time_async_step(
        timings,
        "attraction_lookup_ms",
        get_attraction_context(attraction_name, session=session),
    )
    profile = await _time_async_step(
        timings,
        "profile_lookup_ms",
        get_profile_context(user_id, session=session),
    )

    live_info = None
    weather = None
    navigation = None

    if intent == "live_info":
        live_info = await _time_async_step(
            timings,
            "live_info_lookup_ms",
            get_live_info_context(query, attraction.name if attraction else attraction_name),
        )

    if intent == "weather_info":
        weather_target, weather_resolution_debug = await _resolve_weather_target(query, attraction, session_context)
        timings["weather_target_resolution_ms"] = int(weather_resolution_debug.get("total_ms", 0))
        timings["weather_target_source"] = weather_resolution_debug.get("source")
        timings["weather_target_fallback_ms"] = weather_resolution_debug.get("fallback_ms")
        timings["weather_target_default_ms"] = weather_resolution_debug.get("default_ms")
        timings["weather_target_location_name"] = weather_target
        weather = await _time_async_step(
            timings,
            "weather_lookup_ms",
            get_weather_context(weather_target),
        )

    if intent == "navigation_text":
        slot_result, navigation_resolution_debug = await _resolve_navigation_slots(query, attraction, session_context)
        timings["navigation_slot_resolution_ms"] = int(navigation_resolution_debug.get("total_ms", 0))
        timings["navigation_slot_source"] = navigation_resolution_debug.get("source")
        timings["navigation_slot_fallback_ms"] = navigation_resolution_debug.get("fallback_ms")
        timings["navigation_slot_request_kind"] = slot_result.request_kind
        navigation = await _time_async_step(
            timings,
            "navigation_lookup_ms",
            get_navigation_context(slot_result=_to_navigation_slot_payload(slot_result)),
        )

    rag_needed = should_use_rag_fallback(intent=intent, query=query, attraction=attraction)
    timings["rag_needed"] = rag_needed
    rag_context = None
    if rag_needed:
        rag_context = await _time_async_step(
            timings,
            "rag_lookup_ms",
            get_rag_context(query=query, attraction=attraction),
        )
    else:
        timings["rag_lookup_ms"] = 0

    prompt_projection_started_at = perf_counter()
    prompt_safe_attraction = project_attraction_for_prompt(attraction)
    prompt_safe_profile = project_profile_for_prompt(profile)
    timings["prompt_projection_ms"] = _elapsed_ms(prompt_projection_started_at)
    timings["total_ms"] = _elapsed_ms(started_at)

    return HybridContext(
        attraction=attraction,
        profile=profile,
        live_info=live_info,
        weather=weather,
        navigation=navigation,
        rag=rag_context,
        prompt_safe_attraction=prompt_safe_attraction,
        prompt_safe_profile=prompt_safe_profile,
        session_context=session_context,
        dialogue_history=dialogue_history,
        build_debug={"timings_ms": timings},
    )


async def _resolve_weather_target(query: str, attraction, session_context: dict) -> tuple[str | None, dict[str, object]]:
    started_at = perf_counter()
    rule_started_at = perf_counter()
    rule_target = _resolve_weather_target_by_rule(query, attraction, session_context)
    rule_ms = _elapsed_ms(rule_started_at)
    if rule_target:
        return rule_target, {
            "source": "rule",
            "rule_ms": rule_ms,
            "fallback_ms": 0,
            "default_ms": 0,
            "total_ms": _elapsed_ms(started_at),
        }

    fallback_target = _as_str(session_context.get("weather_location_name"))
    if fallback_target:
        return fallback_target, {
            "source": "fallback",
            "rule_ms": rule_ms,
            "fallback_ms": 0,
            "default_ms": 0,
            "total_ms": _elapsed_ms(started_at),
        }

    default_started_at = perf_counter()
    default_target = _resolve_default_weather_target(session_context)
    default_ms = _elapsed_ms(default_started_at)
    return default_target, {
        "source": "default_city",
        "rule_ms": rule_ms,
        "fallback_ms": 0,
        "default_ms": default_ms,
        "total_ms": _elapsed_ms(started_at),
    }



def _resolve_weather_target_by_rule(query: str, attraction, session_context: dict) -> str | None:
    current_stop_name = _as_str(session_context.get("current_stop_name"))
    next_stop_name = _as_str(session_context.get("next_stop_name"))
    for candidate in [
        attraction.name if attraction else None,
        current_stop_name if current_stop_name and current_stop_name in query else None,
        next_stop_name if next_stop_name and next_stop_name in query else None,
        current_stop_name,
        next_stop_name,
    ]:
        if candidate:
            return candidate
    return None


def _resolve_default_weather_target(session_context: dict) -> str:
    city_code = _as_str(session_context.get("city_code"))
    if city_code:
        return _CITY_CODE_TO_WEATHER_LOCATION.get(city_code.lower(), "Beijing")
    return "Beijing"


async def _resolve_navigation_slots(query: str, attraction, session_context: dict) -> tuple[NavigationSlotResult, dict[str, object]]:
    started_at = perf_counter()
    clarification_selection = _navigation_slot_from_clarification_selection(
        session_context.get("navigation_clarification_selection")
    )
    if clarification_selection is not None:
        return clarification_selection, {
            "source": "clarification_selection",
            "rule_ms": 0,
            "fallback_ms": 0,
            "default_ms": 0,
            "total_ms": _elapsed_ms(started_at),
        }

    rule_started_at = perf_counter()
    rule_result = _extract_navigation_slots_by_rule(query, attraction, session_context)
    rule_ms = _elapsed_ms(rule_started_at)
    if rule_result is not None:
        return rule_result, {
            "source": "rule",
            "rule_ms": rule_ms,
            "fallback_ms": 0,
            "default_ms": 0,
            "total_ms": _elapsed_ms(started_at),
        }

    fallback_started_at = perf_counter()
    fallback_result, _ = await resolve_navigation_slot_fallback(
        query=query,
        raw_query=query,
        pivot_query=query,
        session_context=session_context,
        candidate_places=navigation_candidate_places(),
        rule_result={"intent": "navigation_text", "signals": ["rule_slot_extraction_missed"]},
    )
    fallback_ms = _elapsed_ms(fallback_started_at)
    if fallback_result is not None:
        hydrated = _hydrate_navigation_slots(fallback_result, attraction, session_context)
        if hydrated is not None:
            return hydrated, {
                "source": "fallback",
                "rule_ms": rule_ms,
                "fallback_ms": fallback_ms,
                "default_ms": 0,
                "total_ms": _elapsed_ms(started_at),
            }

    default_started_at = perf_counter()
    current_stop_name = _as_str(session_context.get("current_stop_name"))
    next_stop_name = _as_str(session_context.get("next_stop_name"))
    fallback_destination = attraction.name if attraction else next_stop_name
    default_result = NavigationSlotResult(
        origin=current_stop_name,
        destinations=[fallback_destination] if fallback_destination else [],
        mode="walking",
        mode_source="config_default",
        transit_preference=None,
        source="rule",
        request_kind="unknown",
        reason="missing_origin_or_destination",
    )
    default_ms = _elapsed_ms(default_started_at)
    return default_result, {
        "source": "default_route_context",
        "rule_ms": rule_ms,
        "fallback_ms": fallback_ms,
        "default_ms": default_ms,
        "total_ms": _elapsed_ms(started_at),
    }


def _extract_navigation_slots_by_rule(
    query: str,
    attraction,
    session_context: dict,
) -> NavigationSlotResult | None:
    normalized = _normalize_navigation_query(query)
    current_stop_name = _as_str(session_context.get("current_stop_name"))
    next_stop_name = _as_str(session_context.get("next_stop_name"))

    if any(pattern in normalized for pattern in NAVIGATION_NEXT_STOP_PATTERNS):
        mode, mode_source, transit_preference = _extract_navigation_mode(query)
        return _hydrate_navigation_slots(NavigationSlotResult(
            origin=current_stop_name,
            destinations=[next_stop_name] if next_stop_name else [],
            mode=mode,
            mode_source=mode_source,
            transit_preference=transit_preference,
            source="rule",
            request_kind="next_stop",
            reason=None if current_stop_name and next_stop_name else "missing_origin_or_destination",
        ), attraction, session_context)

    explicit_route = _extract_explicit_route(query)
    if explicit_route is not None:
        return _hydrate_navigation_slots(explicit_route, attraction, session_context)

    destination_only = _extract_destination_only_route(query)
    if destination_only is not None:
        return _hydrate_navigation_slots(destination_only, attraction, session_context)

    if attraction and current_stop_name and attraction.name != current_stop_name:
        mode, mode_source, transit_preference = _extract_navigation_mode(query)
        return _hydrate_navigation_slots(NavigationSlotResult(
            origin=current_stop_name,
            destinations=[attraction.name],
            mode=mode,
            mode_source=mode_source,
            transit_preference=transit_preference,
            source="rule",
            request_kind="destination_only",
            reason=None,
        ), attraction, session_context)
    return None


def _extract_explicit_route(query: str) -> NavigationSlotResult | None:
    normalized = _normalize_navigation_query(query)
    if "从" not in normalized or ("到" not in normalized and "前往" not in normalized):
        return None
    from_positions = [index for index in range(len(normalized)) if normalized.startswith("从", index)]
    for position in reversed(from_positions):
        tail = normalized[position + 1:]
        if "到" in tail:
            origin_text, remainder = tail.split("到", 1)
        elif "前往" in tail:
            origin_text, remainder = tail.split("前往", 1)
        else:
            continue
        origin_fragment = _clean_navigation_place_fragment(origin_text)
        origin_is_current_stop = _is_current_stop_reference(origin_fragment)
        if is_current_location_reference(origin_fragment):
            origin = "当前位置"
        elif origin_is_current_stop:
            origin = "当前站"
        else:
            origin = _canonicalize_navigation_place(origin_fragment)
        destinations = _extract_destination_segments(remainder)
        if origin and destinations:
            mode, mode_source, transit_preference = _extract_navigation_mode(query)
            if len(destinations) > 1:
                request_kind = "multi_leg"
            elif origin_is_current_stop:
                request_kind = "destination_only"
            else:
                request_kind = "explicit_route"
            return NavigationSlotResult(
                origin=origin,
                destinations=destinations,
                mode=mode,
                mode_source=mode_source,
                transit_preference=transit_preference,
                source="rule",
                request_kind=request_kind,
                reason=None,
            )
    return None


def _extract_destination_only_route(query: str) -> NavigationSlotResult | None:
    normalized = _normalize_navigation_query(query)
    if not any(token in normalized for token in ("怎么走", "怎么去", "导航", "路线")):
        return None
    mode, mode_source, transit_preference = _extract_navigation_mode(query)
    if normalized.startswith("去") or normalized.startswith("到"):
        destination_text = _clean_navigation_place_fragment(normalized[1:])
        destinations = _extract_destination_segments(destination_text)
        if destinations:
            request_kind = "multi_leg" if len(destinations) > 1 else "destination_only"
            return NavigationSlotResult(
                origin=None,
                destinations=destinations,
                mode=mode,
                mode_source=mode_source,
                transit_preference=transit_preference,
                source="rule",
                request_kind=request_kind,
                reason=None,
                )
    for prefix in ("带我去", "我想去", "我要去", "想去", "导航到", "走到", "前往", "从这里去", "从这儿去"):
        if prefix in normalized:
            destination_text = _clean_navigation_place_fragment(normalized.split(prefix, 1)[1])
            destinations = _extract_destination_segments(destination_text)
            if destinations:
                request_kind = "multi_leg" if len(destinations) > 1 else "destination_only"
                return NavigationSlotResult(
                    origin=None,
                    destinations=destinations,
                    mode=mode,
                    mode_source=mode_source,
                    transit_preference=transit_preference,
                    source="rule",
                    request_kind=request_kind,
                    reason=None,
                )
    for marker in ("导航到", "带我去", "我想去", "我要去", "准备去", "打算去", "接着去", "然后去", "前往", "走到", "去", "到"):
        marker_positions = [index for index in range(len(normalized)) if normalized.startswith(marker, index)]
        for position in reversed(marker_positions):
            destination_text = _clean_navigation_place_fragment(normalized[position + len(marker):])
            destinations = _extract_destination_segments(destination_text)
            if destinations:
                request_kind = "multi_leg" if len(destinations) > 1 else "destination_only"
                return NavigationSlotResult(
                    origin=None,
                    destinations=destinations,
                    mode=mode,
                    mode_source=mode_source,
                    transit_preference=transit_preference,
                    source="rule",
                    request_kind=request_kind,
                    reason=None,
                )
    return None


def _extract_destination_segments(text: str) -> list[str]:
    normalized = text.replace("，", " ").replace(",", " ").replace("。", " ").replace("?", " ").replace("？", " ")
    for separator in NAVIGATION_MULTI_STOP_PATTERNS:
        normalized = normalized.replace(separator, "|")
    normalized = normalized.replace("到", "|")
    cleaned = normalized
    for marker in ("怎么走", "怎么去", "如何到达", "路线", "导航"):
        cleaned = cleaned.replace(marker, " ")
    raw_segments = [segment for segment in cleaned.split("|") if segment.strip()]
    candidates = [_clean_navigation_place_fragment(segment) for segment in raw_segments]
    destinations: list[str] = []
    for candidate in candidates:
        if not candidate or _is_navigation_placeholder_fragment(candidate):
            continue
        canonical = _canonicalize_navigation_place(candidate)
        if canonical and canonical not in destinations:
            destinations.append(canonical)
    return destinations


def _is_navigation_placeholder_fragment(text: str) -> bool:
    stripped = text.strip(" ，。！？?；;：:")
    return stripped in {"哪里", "哪儿", "哪边", "哪一个", "哪个", "下一个", "下一站", "下个点", "下个地方"}


def _is_current_stop_reference(text: str | None) -> bool:
    stripped = (text or "").strip(" ，。！？?；;：:")
    return any(
        marker in stripped
        for marker in (
            "当前站",
            "当前站点",
            "现在这个站",
            "现在这个站点",
            "现在的站",
            "原站点",
        )
    )


def _hydrate_navigation_slots(
    slot_result: NavigationSlotResult,
    attraction,
    session_context: dict,
) -> NavigationSlotResult | None:
    current_stop_name = _as_str(session_context.get("current_stop_name"))
    next_stop_name = _as_str(session_context.get("next_stop_name"))
    gps_origin = make_gps_navigation_place(session_context.get("current_position"))
    origin_place = None if is_current_location_reference(slot_result.origin) else resolve_navigation_place(slot_result.origin)
    origin = origin_place.name if origin_place else None

    destinations = []
    destination_places = []
    for destination in slot_result.destinations:
        place = resolve_navigation_place(destination)
        if place is None or not place.name:
            continue
        if place.name not in destinations:
            destinations.append(place.name)
            destination_places.append(place)

    if not destinations and attraction is not None:
        attraction_place = resolve_navigation_place(attraction.name)
        if attraction_place is not None and attraction_place.name:
            destinations = [attraction_place.name]
            destination_places = [attraction_place]
        else:
            destinations = [attraction.name]
    if slot_result.request_kind == "next_stop" and not destinations and next_stop_name:
        next_stop_place = resolve_navigation_place(next_stop_name)
        destinations = [next_stop_place.name if next_stop_place and next_stop_place.name else next_stop_name]
        destination_places = [next_stop_place] if next_stop_place is not None else []
    if (
        slot_result.request_kind in {"destination_only", "next_stop"}
        or is_current_location_reference(slot_result.origin)
    ) and gps_origin is not None:
        origin_place = gps_origin
        origin = gps_origin.name
    elif _is_current_stop_reference(slot_result.origin):
        origin_place = resolve_navigation_place(current_stop_name)
        origin = origin_place.name if origin_place else current_stop_name
    elif (
        slot_result.request_kind in {"destination_only", "next_stop", "multi_leg", "unknown"}
        or is_current_location_reference(slot_result.origin)
    ) and origin is None:
        origin_place = resolve_navigation_place(current_stop_name)
        origin = origin_place.name if origin_place else current_stop_name
    reason = slot_result.reason
    if origin is None or not destinations:
        reason = reason or "missing_origin_or_destination"
    mode, mode_source = _resolve_navigation_mode_for_hydrated_slot(
        slot_result,
        origin_place=origin_place,
        destination_places=destination_places,
    )
    transit_preference = slot_result.transit_preference if mode == "transit" else None
    if mode == "transit" and mode_source == "distance_default" and transit_preference is None:
        transit_preference = "public_transport"
    return NavigationSlotResult(
        origin=origin,
        destinations=destinations,
        origin_place=_navigation_place_for_slot_result(origin_place),
        destination_places=[
            place_result
            for place in destination_places
            if (place_result := _navigation_place_for_slot_result(place)) is not None
        ],
        mode=mode,
        mode_source=mode_source,
        transit_preference=transit_preference,
        source=slot_result.source,
        request_kind=slot_result.request_kind,
        reason=reason,
    )


def _to_navigation_slot_payload(slot_result: NavigationSlotResult) -> NavigationSlotPayload:
    return NavigationSlotPayload(**slot_result.model_dump())


def _navigation_slot_from_clarification_selection(selection: object) -> NavigationSlotResult | None:
    if not isinstance(selection, dict):
        return None
    selection_error = selection.get("selection_error")
    if selection_error:
        slot_payload = selection.get("slot_result")
        if not isinstance(slot_payload, dict):
            return None
        try:
            slot_result = NavigationSlotResult(**slot_payload)
        except Exception:
            return None
        reason = str(selection_error)
        if selection_error == "selection_index_out_of_range":
            candidate_count = _safe_int(selection.get("candidate_count"))
            selected_index = _safe_int(selection.get("selected_index"))
            reason = f"selection_index_out_of_range:{selected_index}:{candidate_count}"
        return NavigationSlotResult(
            **{
                **slot_result.model_dump(),
                "reason": reason,
            }
        )
    slot_payload = selection.get("slot_result")
    candidate = selection.get("candidate")
    if not isinstance(slot_payload, dict) or not isinstance(candidate, dict):
        return None
    try:
        slot_result = NavigationSlotResult(**slot_payload)
    except Exception:
        return None

    target_role = str(selection.get("target_role") or "destination")
    target_index = _safe_int(selection.get("target_index")) or 0
    candidate_place = {
        "raw_text": candidate.get("raw_text") or candidate.get("name"),
        "place_id": candidate.get("place_id"),
        "name": candidate.get("name"),
        "display_name": candidate.get("display_name") or candidate.get("name"),
        "latitude": candidate.get("latitude"),
        "longitude": candidate.get("longitude"),
        "city": "北京市",
        "adcode": candidate.get("adcode"),
        "source": candidate.get("source") or "amap_candidate",
        "confidence": candidate.get("confidence") or 0.8,
        "reason": "clarification_selection",
    }
    if target_role == "origin":
        return NavigationSlotResult(
            **{
                **slot_result.model_dump(),
                "origin": candidate_place["name"],
                "origin_place": candidate_place,
                "reason": "clarification_selection",
            }
        )

    destinations = list(slot_result.destinations)
    destination_places = [
        place.model_dump() if hasattr(place, "model_dump") else place
        for place in slot_result.destination_places
    ]
    while len(destinations) <= target_index:
        destinations.append("")
    while len(destination_places) <= target_index:
        destination_places.append({})
    destinations[target_index] = str(candidate_place["name"] or destinations[target_index])
    destination_places[target_index] = candidate_place
    return NavigationSlotResult(
        **{
            **slot_result.model_dump(),
            "destinations": destinations,
            "destination_places": destination_places,
            "reason": "clarification_selection",
        }
    )


def _normalize_navigation_query(query: str) -> str:
    return query.replace("？", "").replace("?", "").replace("。", "").replace("，", " ").replace(",", " ").strip()


def _clean_navigation_place_fragment(text: str | None) -> str:
    cleaned = (text or "").strip()
    for prefix in ("去", "到"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    for suffix in ("入口怎么找", "怎么找", "怎么走", "怎么去", "如何到达", "路线", "导航", "走", "去", "到"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned


def _extract_navigation_mode(query: str) -> tuple[str, str, str | None]:
    normalized = _normalize_navigation_query(query)
    if _contains_unnegated_navigation_mode(normalized, ("步行", "走路", "步行路线", "走过去", "走着去")):
        return "walking", "explicit", None
    if _contains_unnegated_navigation_mode(normalized, ("开车", "驾车", "自驾", "打车")):
        return "driving", "explicit", None
    transit_preference = _extract_transit_preference(normalized)
    if transit_preference is not None:
        return "transit", "explicit", transit_preference
    return "walking", "config_default", None


def _extract_transit_preference(normalized_query: str) -> str | None:
    has_subway = _contains_unnegated_navigation_mode(
        normalized_query,
        ("地铁", "坐地铁", "乘地铁", "几号线", "地铁换乘"),
    )
    has_bus = _contains_unnegated_navigation_mode(
        normalized_query,
        ("公交", "公交车", "坐公交", "乘公交", "巴士"),
    )
    has_public_transport = _contains_unnegated_navigation_mode(
        normalized_query,
        ("公共交通", "公交地铁", "公交或地铁", "公交和地铁", "地铁公交", "坐车", "换乘"),
    )
    if has_bus and has_subway:
        return "public_transport"
    if has_bus:
        return "bus"
    if has_subway:
        return "subway"
    if has_public_transport:
        return "public_transport"
    return None


def _contains_unnegated_navigation_mode(text: str, tokens: tuple[str, ...]) -> bool:
    negation_markers = ("不", "别", "不要", "不用", "不是", "不坐", "别坐")
    for token in tokens:
        start = 0
        while True:
            index = text.find(token, start)
            if index < 0:
                break
            prefix = text[max(0, index - 4):index]
            if not any(marker in prefix for marker in negation_markers):
                return True
            start = index + len(token)
    return False


def _resolve_navigation_mode_for_hydrated_slot(
    slot_result: NavigationSlotResult,
    *,
    origin_place,
    destination_places: list,
) -> tuple[str, str]:
    if slot_result.mode_source == "explicit":
        return slot_result.mode, slot_result.mode_source
    max_leg_distance = _max_straight_line_leg_distance_meters(origin_place, destination_places)
    if max_leg_distance is not None and max_leg_distance > _DEFAULT_TRANSIT_THRESHOLD_METERS:
        return "transit", "distance_default"
    return "walking", "distance_default" if max_leg_distance is not None else "config_default"


def _max_straight_line_leg_distance_meters(origin_place, destination_places: list) -> int | None:
    current = origin_place
    distances: list[int] = []
    for destination in destination_places:
        distance = _straight_line_distance_meters(current, destination)
        if distance is not None:
            distances.append(distance)
        current = destination
    return max(distances) if distances else None


def _straight_line_distance_meters(origin_place, destination_place) -> int | None:
    if (
        origin_place is None
        or destination_place is None
        or origin_place.latitude is None
        or origin_place.longitude is None
        or destination_place.latitude is None
        or destination_place.longitude is None
    ):
        return None
    earth_radius_meters = 6371000
    origin_lat = radians(float(origin_place.latitude))
    destination_lat = radians(float(destination_place.latitude))
    lat_delta = radians(float(destination_place.latitude) - float(origin_place.latitude))
    lon_delta = radians(float(destination_place.longitude) - float(origin_place.longitude))
    haversine = sin(lat_delta / 2) ** 2 + cos(origin_lat) * cos(destination_lat) * sin(lon_delta / 2) ** 2
    return int(earth_radius_meters * 2 * asin(sqrt(haversine)))


def _canonicalize_navigation_place(text: str | None) -> str | None:
    place = resolve_navigation_place(text)
    return place.name if place is not None else None


def _navigation_place_for_slot_result(place) -> dict[str, object] | None:
    if place is None:
        return None
    if hasattr(place, "model_dump"):
        return place.model_dump()
    if isinstance(place, dict):
        return place
    return None


async def _time_async_step(timings: dict[str, int | str | bool | None], key: str, awaitable):
    started_at = perf_counter()
    result = await awaitable
    timings[key] = _elapsed_ms(started_at)
    return result



def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)



def _as_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _safe_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
