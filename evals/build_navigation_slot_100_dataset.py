from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT = Path("evals/datasets/navigation_slot_100_cases.json")

PLACES = [
    ("Tiananmen Square", "天安门", "tiananmen_square"),
    ("Forbidden City", "故宫", "forbidden_city"),
    ("Jingshan Park", "景山", "jingshan_park"),
    ("Temple of Heaven", "天坛", "temple_of_heaven"),
    ("Summer Palace", "颐和园", "summer_palace"),
    ("Yuanmingyuan Park", "圆明园", "yuanmingyuan_park"),
    ("Beihai Park", "北海公园", "beihai_park"),
    ("Shichahai", "什刹海", "shichahai"),
    ("Nanluoguxiang", "南锣鼓巷", "nanluoguxiang"),
    ("Yonghe Temple", "雍和宫", "yonghe_temple"),
    ("Prince Gong's Mansion", "恭王府", "prince_gong_mansion"),
    ("Zhengyangmen", "正阳门", "zhengyangmen"),
]
PLACE_BY_CANONICAL = {canonical: (zh, place_id) for canonical, zh, place_id in PLACES}

GPS_CONTEXT = {"current_position": {"latitude": 39.905, "longitude": 116.3976}, "city_code": "beijing"}
ROUTE_CONTEXT = {"current_stop_name": "Tiananmen Square", "next_stop_name": "Forbidden City", "city_code": "beijing"}


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
    notes: str,
    expected_mode: str | None = None,
) -> dict[str, Any]:
    case = {
        "case_id": case_id,
        "category": category,
        "query": query,
        "language": "zh",
        "session_context": session_context,
        "expected_intent": "navigation_text",
        "expected_request_kind": request_kind,
        "expected_origin": origin,
        "expected_destinations": destinations,
        "expected_source": "rule",
        "expected_origin_place_id": origin_place_id,
        "expected_destination_place_ids": [PLACE_BY_CANONICAL[destination][1] for destination in destinations],
        "notes": notes,
    }
    if expected_mode is not None:
        case["expected_mode"] = expected_mode
    return case


def boundary_case(case_id: str, category: str, query: str, expected_intent: str, notes: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": category,
        "query": query,
        "language": "zh",
        "session_context": ROUTE_CONTEXT,
        "expected_intent": expected_intent,
        "notes": notes,
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    next_stop_queries = [
        "下一站怎么去？",
        "下一站怎么走？",
        "接下来怎么去？",
        "接下来怎么走？",
        "去下一站怎么走？",
    ]
    for index in range(15):
        query = next_stop_queries[index % len(next_stop_queries)]
        context = {
            **ROUTE_CONTEXT,
            **({"current_position": {"latitude": 39.905 + index * 0.0001, "longitude": 116.3976}} if index < 8 else {}),
        }
        origin = "当前位置" if "current_position" in context else "Tiananmen Square"
        origin_place_id = "gps_current_position" if "current_position" in context else "tiananmen_square"
        cases.append(
            navigation_case(
                f"NAV100-NS-{index + 1:03d}",
                "next_stop",
                query,
                request_kind="next_stop",
                origin=origin,
                destinations=["Forbidden City"],
                session_context=context,
                origin_place_id=origin_place_id,
                notes="下一站问法，优先 GPS，否则 current_stop。",
            )
        )

    destination_templates = [
        "去{zh}怎么走？",
        "到{zh}怎么去？",
        "导航到{zh}怎么走？",
        "我想去{zh}，怎么走？",
        "带我导航到{zh}入口怎么走？",
    ]
    for index in range(15):
        canonical, zh, place_id = PLACES[(index + 1) % len(PLACES)]
        query = destination_templates[index % len(destination_templates)].format(zh=zh)
        cases.append(
            navigation_case(
                f"NAV100-DGPS-{index + 1:03d}",
                "destination_only_gps",
                query,
                request_kind="destination_only",
                origin="当前位置",
                destinations=[canonical],
                session_context={**GPS_CONTEXT, "current_stop_name": "Tiananmen Square"},
                origin_place_id="gps_current_position",
                notes=f"目的地型导航，GPS 起点，目的地={place_id}。",
            )
        )

    for index in range(15):
        canonical, zh, place_id = PLACES[(index + 3) % len(PLACES)]
        query = destination_templates[(index + 2) % len(destination_templates)].format(zh=zh)
        cases.append(
            navigation_case(
                f"NAV100-DCTX-{index + 1:03d}",
                "destination_only_current_stop",
                query,
                request_kind="destination_only",
                origin="Forbidden City",
                destinations=[canonical],
                session_context={"current_stop_name": "Forbidden City", "next_stop_name": "Jingshan Park", "city_code": "beijing"},
                origin_place_id="forbidden_city",
                notes=f"目的地型导航，无 GPS，用 current_stop 起点，目的地={place_id}。",
            )
        )

    route_pairs = [
        ("Tiananmen Square", "Forbidden City"),
        ("Forbidden City", "Jingshan Park"),
        ("Temple of Heaven", "Zhengyangmen"),
        ("Beihai Park", "Shichahai"),
        ("Nanluoguxiang", "Yonghe Temple"),
        ("Summer Palace", "Yuanmingyuan Park"),
        ("Zhengyangmen", "Tiananmen Square"),
        ("Prince Gong's Mansion", "Beihai Park"),
        ("Shichahai", "Nanluoguxiang"),
        ("Yonghe Temple", "Temple of Heaven"),
    ]
    explicit_templates = [
        "从{a}到{b}怎么走？",
        "从{a}怎么走到{b}？",
        "请给我从{a}到{b}的文字路线。",
        "从{a}前往{b}怎么走？",
    ]
    for index in range(20):
        origin, destination = route_pairs[index % len(route_pairs)]
        origin_zh, origin_id = PLACE_BY_CANONICAL[origin]
        destination_zh, _ = PLACE_BY_CANONICAL[destination]
        query = explicit_templates[index % len(explicit_templates)].format(a=origin_zh, b=destination_zh)
        cases.append(
            navigation_case(
                f"NAV100-EXP-{index + 1:03d}",
                "explicit_route",
                query,
                request_kind="explicit_route",
                origin=origin,
                destinations=[destination],
                session_context={"city_code": "beijing"},
                origin_place_id=origin_id,
                notes="显式起终点，不应使用 GPS/current_stop 覆盖。",
            )
        )

    multi_routes = [
        ("Tiananmen Square", ["Forbidden City", "Jingshan Park"]),
        ("Temple of Heaven", ["Zhengyangmen", "Tiananmen Square"]),
        ("Beihai Park", ["Shichahai", "Nanluoguxiang", "Yonghe Temple"]),
        ("Summer Palace", ["Yuanmingyuan Park", "Beihai Park"]),
        ("Prince Gong's Mansion", ["Beihai Park", "Jingshan Park", "Forbidden City"]),
    ]
    for index in range(20):
        origin, destinations = multi_routes[index % len(multi_routes)]
        origin_zh, origin_id = PLACE_BY_CANONICAL[origin]
        destination_zh = [PLACE_BY_CANONICAL[destination][0] for destination in destinations]
        connector = "再到" if index % 2 == 0 else "再去"
        query = f"从{origin_zh}到{destination_zh[0]}{connector}{connector.join(destination_zh[1:])}怎么走？"
        cases.append(
            navigation_case(
                f"NAV100-MULTI-{index + 1:03d}",
                "multi_leg",
                query,
                request_kind="multi_leg",
                origin=origin,
                destinations=destinations,
                session_context={"city_code": "beijing"},
                origin_place_id=origin_id,
                notes="多段路线按用户顺序拆成连续 legs。",
            )
        )

    disambiguation_queries = [
        ("到天坛怎么走？", "Temple of Heaven", "temple_of_heaven"),
        ("从故宫到天坛怎么走？", "Temple of Heaven", "forbidden_city"),
        ("导航到祈年殿怎么走？", "Temple of Heaven", "gps_current_position"),
        ("从前门到天坛怎么走？", "Temple of Heaven", "zhengyangmen"),
        ("去圆明园怎么走？", "Yuanmingyuan Park", "gps_current_position"),
        ("从颐和园到圆明园怎么走？", "Yuanmingyuan Park", "summer_palace"),
        ("到北海怎么去？", "Beihai Park", "gps_current_position"),
        ("从后海到南锣鼓巷怎么走？", "Nanluoguxiang", "shichahai"),
        ("到雍和宫怎么走？", "Yonghe Temple", "gps_current_position"),
        ("从正阳门到天安门广场怎么走？", "Tiananmen Square", "zhengyangmen"),
    ]
    for index, (query, destination, origin_place_id) in enumerate(disambiguation_queries, 1):
        if query.startswith("从"):
            origin = {
                "forbidden_city": "Forbidden City",
                "zhengyangmen": "Zhengyangmen",
                "summer_palace": "Summer Palace",
                "shichahai": "Shichahai",
            }.get(origin_place_id, "Zhengyangmen")
            kind = "explicit_route"
            context = {"city_code": "beijing"}
        else:
            origin = "当前位置"
            kind = "destination_only"
            context = {**GPS_CONTEXT, "current_stop_name": "Tiananmen Square"}
            origin_place_id = "gps_current_position"
        cases.append(
            navigation_case(
                f"NAV100-BJ-{index:03d}",
                "beijing_disambiguation",
                query,
                request_kind=kind,
                origin=origin,
                destinations=[destination],
                session_context=context,
                origin_place_id=origin_place_id,
                notes="北京景点同名/别名消歧，尤其天坛不能漂到外地。",
            )
        )

    boundary_cases = [
        ("把下一站删掉。", "manual_route_edit_redirect", "删点是改路线，不是导航。"),
        ("把后面路线改轻松一点。", "manual_route_edit_redirect", "调整路线是人工改路线。"),
        ("接下来怎么安排？", "trip_assistant", "问安排，不是点到点导航。"),
        ("故宫之后去哪会比较顺？", "trip_assistant", "问下一站策略，不是导航步骤。"),
    ]
    for index, (query, expected_intent, notes) in enumerate(boundary_cases, 1):
        cases.append(boundary_case(f"NAV100-BND-{index:03d}", "boundary_negative", query, expected_intent, notes))
    cases.append(
        navigation_case(
            "NAV100-BND-005",
            "boundary_negative",
            "从天安门到天坛坐几号线换乘？",
            request_kind="explicit_route",
            origin="Tiananmen Square",
            destinations=["Temple of Heaven"],
            session_context=ROUTE_CONTEXT,
            origin_place_id="tiananmen_square",
            expected_mode="transit",
            notes="公交/地铁换乘已支持，应进入公共交通文字导航。",
        )
    )

    assert len(cases) == 100
    return cases


def main() -> None:
    payload = {
        "dataset_name": "navigation_slot_100_cases",
        "dataset_version": "2026-05-15",
        "notes": "Navigation intent slot benchmark covering next-stop, destination-only, explicit route, multi-leg, Beijing place disambiguation, and boundary negatives.",
        "cases": build_cases(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(payload['cases'])} cases to {OUT}")


if __name__ == "__main__":
    main()
