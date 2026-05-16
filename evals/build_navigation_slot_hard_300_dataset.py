from __future__ import annotations

import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

from yoyo.modules.knowledge.place_resolver import REGISTERED_NAVIGATION_PLACES, RegisteredNavigationPlace


OUT = Path("evals/datasets/navigation_slot_hard_300_cases.json")
TRANSIT_THRESHOLD_METERS = 3000

PLACES = {place.name: place for place in REGISTERED_NAVIGATION_PLACES}

SHORT_PAIRS = [
    ("Tiananmen Square", "Forbidden City"),
    ("Forbidden City", "Jingshan Park"),
    ("Beihai Park", "Shichahai"),
    ("Shichahai", "Nanluoguxiang"),
    ("Prince Gong's Mansion", "Beihai Park"),
    ("Zhengyangmen", "Tiananmen Square"),
    ("Summer Palace", "Yuanmingyuan Park"),
]

LONG_PAIRS = [
    ("Forbidden City", "Temple of Heaven"),
    ("Tiananmen Square", "Yonghe Temple"),
    ("Forbidden City", "Summer Palace"),
    ("Temple of Heaven", "Beihai Park"),
    ("Yuanmingyuan Park", "Yonghe Temple"),
    ("Summer Palace", "Beihai Park"),
    ("Zhengyangmen", "Yonghe Temple"),
]

MULTI_ROUTES = [
    ("Tiananmen Square", ["Forbidden City", "Jingshan Park"]),
    ("Beihai Park", ["Shichahai", "Nanluoguxiang"]),
    ("Temple of Heaven", ["Zhengyangmen", "Tiananmen Square"]),
    ("Forbidden City", ["Jingshan Park", "Beihai Park", "Shichahai"]),
    ("Beihai Park", ["Shichahai", "Nanluoguxiang", "Yonghe Temple"]),
    ("Summer Palace", ["Yuanmingyuan Park", "Beihai Park"]),
    ("Prince Gong's Mansion", ["Beihai Park", "Jingshan Park", "Forbidden City"]),
    ("Zhengyangmen", ["Tiananmen Square", "Forbidden City", "Jingshan Park"]),
]

MODE_VARIANTS = [
    ("unspecified", "", None, None),
    ("explicit_walking", "步行", "walking", "explicit"),
    ("explicit_driving", "打车", "driving", "explicit"),
    ("explicit_transit_metro", "坐地铁", "transit", "explicit"),
    ("explicit_transit_bus", "坐公交", "transit", "explicit"),
    ("negated_transit_walking", "不坐地铁，步行", "walking", "explicit"),
]

NEXT_STOP_TEMPLATES = [
    "刚从展厅出来，老人也休息好了，下一站怎么去{tail}？",
    "故宫这一段拍照花了不少时间，但我们不改路线，下一站怎么走{tail}？",
    "孩子现在体力还行，先别推荐别的点，接下来怎么去{tail}？",
    "讲解先停一下，我只想看文字路线，接下来怎么走{tail}？",
    "水也买好了，队伍不用管了，去下一站怎么走{tail}？",
]

DESTINATION_TEMPLATES = [
    "刚才拍照耽误了一会儿，下面到{dest}{mode}怎么去？",
    "先不查开放时间，也不用推荐别的景点，导航到{dest}{mode}怎么走？",
    "孩子有点累但还想继续逛，我想去{dest}{mode}怎么走，给文字路线。",
    "别改我的路线，接着去{dest}{mode}怎么走？",
    "我从门口出来以后方向感有点乱，从这里去{dest}{mode}怎么走？",
    "现在不讲历史，单纯告诉我到{dest}{mode}路线怎么走。",
]

EXPLICIT_TEMPLATES = [
    "不用考虑我现在定位，我问两个点之间的路，从{origin}到{dest}{mode}怎么走？",
    "明天可能带父母走这段，先确认一下，从{origin}到{dest}{mode}怎么去？",
    "先别改行程顺序，也不用讲景点故事，从{origin}到{dest}{mode}给我文字路线。",
    "如果只看这一段，从{origin}前往{dest}{mode}怎么走比较清楚？",
    "我在整理备用路线，从{origin}到{dest}{mode}怎么走，尽量分步骤。",
]

MULTI_TEMPLATES = [
    "我不想改顺序，只想先看清楚路，从{origin}到{first}再到{rest}{mode}怎么走？",
    "明天可能带父母走这一串点，先确认文字路线，从{origin}到{first}再去{rest}{mode}怎么走？",
    "不用讲每个景点的历史，单纯看路，从{origin}到{first}再到{rest}{mode}给我分段路线。",
    "我们想少绕路但顺序先不变，从{origin}到{first}再去{rest}{mode}怎么走比较清楚？",
    "请按每两点一段说，从{origin}到{first}再到{rest}{mode}怎么走？",
]


def navigation_case(
    case_id: str,
    category: str,
    query: str,
    *,
    request_kind: str,
    origin: str,
    destinations: list[str],
    session_context: dict[str, Any],
    origin_place_id: str,
    expected_mode: str,
    expected_mode_source: str,
    mode_case: str,
    notes: str,
    sub_category: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": category,
        "sub_category": sub_category,
        "query": query,
        "language": "zh",
        "session_context": session_context,
        "mode_case": mode_case,
        "distance_bucket": _distance_bucket(origin, destinations, session_context),
        "expected_intent": "navigation_text",
        "expected_request_kind": request_kind,
        "expected_origin": origin,
        "expected_destinations": destinations,
        "expected_source": "rule",
        "expected_origin_place_id": origin_place_id,
        "expected_destination_place_ids": [PLACES[destination].place_id for destination in destinations],
        "expected_mode": expected_mode,
        "expected_mode_source": expected_mode_source,
        "notes": notes,
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    cases.extend(_build_next_stop_cases())
    cases.extend(_build_destination_only_cases())
    cases.extend(_build_explicit_route_cases())
    cases.extend(_build_multi_leg_cases())
    assert len(cases) == 300
    return cases


def _build_next_stop_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    route_pairs = SHORT_PAIRS + LONG_PAIRS
    for index in range(60):
        current_stop, next_stop = route_pairs[index % len(route_pairs)]
        mode_case, mode_word, explicit_mode, explicit_source = MODE_VARIANTS[index % len(MODE_VARIANTS)]
        with_gps = index % 3 != 0
        gps_place = PLACES[current_stop]
        context = {
            "current_stop_name": current_stop,
            "next_stop_name": next_stop,
            "city_code": "beijing",
        }
        if with_gps:
            context["current_position"] = _offset_gps(gps_place, index)
        origin = "当前位置" if with_gps else current_stop
        origin_place_id = "gps_current_position" if with_gps else PLACES[current_stop].place_id
        expected_mode, expected_mode_source = _expected_mode(
            explicit_mode,
            explicit_source,
            origin,
            [next_stop],
            context,
        )
        query = NEXT_STOP_TEMPLATES[index % len(NEXT_STOP_TEMPLATES)].format(tail=_next_stop_mode_tail(mode_word))
        cases.append(
            navigation_case(
                f"NAVH-NS-{index + 1:03d}",
                "hard_next_stop",
                query,
                request_kind="next_stop",
                origin=origin,
                destinations=[next_stop],
                session_context=context,
                origin_place_id=origin_place_id,
                expected_mode=expected_mode,
                expected_mode_source=expected_mode_source,
                mode_case=mode_case,
                sub_category="gps" if with_gps else "current_stop",
                notes="下一站导航：从旅行状态取 next_stop，起点优先 GPS。",
            )
        )
    return cases


def _build_destination_only_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    route_pairs = LONG_PAIRS + SHORT_PAIRS
    for index in range(80):
        origin_stop, destination = route_pairs[index % len(route_pairs)]
        mode_case, mode_word, explicit_mode, explicit_source = MODE_VARIANTS[(index + 1) % len(MODE_VARIANTS)]
        with_gps = index % 4 != 0
        context = {
            "current_stop_name": origin_stop,
            "next_stop_name": destination,
            "city_code": "beijing",
        }
        if with_gps:
            context["current_position"] = _offset_gps(PLACES[origin_stop], index)
        origin = "当前位置" if with_gps else origin_stop
        origin_place_id = "gps_current_position" if with_gps else PLACES[origin_stop].place_id
        expected_mode, expected_mode_source = _expected_mode(
            explicit_mode,
            explicit_source,
            origin,
            [destination],
            context,
        )
        query = DESTINATION_TEMPLATES[index % len(DESTINATION_TEMPLATES)].format(
            dest=PLACES[destination].display_name,
            mode=_inline_mode(mode_word),
        )
        cases.append(
            navigation_case(
                f"NAVH-DEST-{index + 1:03d}",
                "hard_destination_only",
                query,
                request_kind="destination_only",
                origin=origin,
                destinations=[destination],
                session_context=context,
                origin_place_id=origin_place_id,
                expected_mode=expected_mode,
                expected_mode_source=expected_mode_source,
                mode_case=mode_case,
                sub_category="gps" if with_gps else "current_stop",
                notes="目的地型导航：query 抽目的地，起点来自 GPS 或 current_stop。",
            )
        )
    return cases


def _build_explicit_route_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    route_pairs = SHORT_PAIRS + LONG_PAIRS
    for index in range(80):
        origin_name, destination = route_pairs[(index * 2) % len(route_pairs)]
        mode_case, mode_word, explicit_mode, explicit_source = MODE_VARIANTS[(index + 2) % len(MODE_VARIANTS)]
        context = {
            "current_stop_name": "Forbidden City",
            "next_stop_name": "Jingshan Park",
            "city_code": "beijing",
            "current_position": _offset_gps(PLACES["Temple of Heaven"], index),
        }
        expected_mode, expected_mode_source = _expected_mode(
            explicit_mode,
            explicit_source,
            origin_name,
            [destination],
            context,
        )
        query = EXPLICIT_TEMPLATES[index % len(EXPLICIT_TEMPLATES)].format(
            origin=PLACES[origin_name].display_name,
            dest=PLACES[destination].display_name,
            mode=_inline_mode(mode_word),
        )
        cases.append(
            navigation_case(
                f"NAVH-EXP-{index + 1:03d}",
                "hard_explicit_route",
                query,
                request_kind="explicit_route",
                origin=origin_name,
                destinations=[destination],
                session_context=context,
                origin_place_id=PLACES[origin_name].place_id,
                expected_mode=expected_mode,
                expected_mode_source=expected_mode_source,
                mode_case=mode_case,
                sub_category="explicit_origin_over_gps",
                notes="显式起终点：不能被 session GPS/current_stop 覆盖。",
            )
        )
    return cases


def _build_multi_leg_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index in range(80):
        origin_name, destinations = MULTI_ROUTES[index % len(MULTI_ROUTES)]
        mode_case, mode_word, explicit_mode, explicit_source = MODE_VARIANTS[(index + 3) % len(MODE_VARIANTS)]
        context = {
            "current_stop_name": "Forbidden City",
            "next_stop_name": "Jingshan Park",
            "city_code": "beijing",
        }
        expected_mode, expected_mode_source = _expected_mode(
            explicit_mode,
            explicit_source,
            origin_name,
            destinations,
            context,
        )
        destination_displays = [PLACES[destination].display_name for destination in destinations]
        query = MULTI_TEMPLATES[index % len(MULTI_TEMPLATES)].format(
            origin=PLACES[origin_name].display_name,
            first=destination_displays[0],
            rest="再到".join(destination_displays[1:]),
            mode=_inline_mode(mode_word),
        )
        cases.append(
            navigation_case(
                f"NAVH-MULTI-{index + 1:03d}",
                "hard_multi_leg",
                query,
                request_kind="multi_leg",
                origin=origin_name,
                destinations=destinations,
                session_context=context,
                origin_place_id=PLACES[origin_name].place_id,
                expected_mode=expected_mode,
                expected_mode_source=expected_mode_source,
                mode_case=mode_case,
                sub_category=f"{len(destinations)}_destinations",
                notes="多段导航：抽取有序 destinations，下游两两拆段调用高德。",
            )
        )
    return cases


def _expected_mode(
    explicit_mode: str | None,
    explicit_source: str | None,
    origin: str,
    destinations: list[str],
    session_context: dict[str, Any],
) -> tuple[str, str]:
    if explicit_mode and explicit_source:
        return explicit_mode, explicit_source
    return _default_mode_by_distance(origin, destinations, session_context), "distance_default"


def _default_mode_by_distance(origin: str, destinations: list[str], session_context: dict[str, Any]) -> str:
    max_distance = _max_leg_distance(origin, destinations, session_context)
    return "transit" if max_distance > TRANSIT_THRESHOLD_METERS else "walking"


def _distance_bucket(origin: str, destinations: list[str], session_context: dict[str, Any]) -> str:
    max_distance = _max_leg_distance(origin, destinations, session_context)
    return "over_3km" if max_distance > TRANSIT_THRESHOLD_METERS else "within_3km"


def _max_leg_distance(origin: str, destinations: list[str], session_context: dict[str, Any]) -> int:
    current_location = _location_for_origin(origin, session_context)
    distances = []
    for destination in destinations:
        destination_place = PLACES[destination]
        distances.append(
            _straight_line_distance_meters(
                current_location,
                (destination_place.longitude, destination_place.latitude),
            )
        )
        current_location = (destination_place.longitude, destination_place.latitude)
    return max(distances)


def _location_for_origin(origin: str, session_context: dict[str, Any]) -> tuple[float, float]:
    if origin == "当前位置":
        position = session_context["current_position"]
        return float(position["longitude"]), float(position["latitude"])
    place = PLACES[origin]
    return place.longitude, place.latitude


def _straight_line_distance_meters(origin_location: tuple[float, float], destination_location: tuple[float, float]) -> int:
    origin_lon, origin_lat_value = origin_location
    destination_lon, destination_lat_value = destination_location
    earth_radius_meters = 6371000
    origin_lat = radians(origin_lat_value)
    destination_lat = radians(destination_lat_value)
    lat_delta = radians(destination_lat_value - origin_lat_value)
    lon_delta = radians(destination_lon - origin_lon)
    haversine = sin(lat_delta / 2) ** 2 + cos(origin_lat) * cos(destination_lat) * sin(lon_delta / 2) ** 2
    return int(earth_radius_meters * 2 * asin(sqrt(haversine)))


def _offset_gps(place: RegisteredNavigationPlace, index: int) -> dict[str, float]:
    lat_offset = ((index % 5) - 2) * 0.00008
    lon_offset = ((index % 7) - 3) * 0.00008
    return {
        "latitude": round(place.latitude + lat_offset, 7),
        "longitude": round(place.longitude + lon_offset, 7),
    }


def _inline_mode(mode_word: str) -> str:
    return f"{mode_word}" if mode_word else ""


def _next_stop_mode_tail(mode_word: str) -> str:
    if not mode_word:
        return ""
    return f"，{mode_word}也可以"


def main() -> None:
    payload = {
        "dataset_name": "navigation_slot_hard_300_cases",
        "dataset_version": "2026-05-15",
        "notes": (
            "300 complex navigation intent cases covering next stop, destination-only, explicit point-to-point, "
            "multi-leg routing, varied GPS origins, over/under 3km defaults, explicit walking/driving/transit, "
            "and mode negation."
        ),
        "cases": build_cases(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(payload['cases'])} cases to {OUT}")


if __name__ == "__main__":
    main()
