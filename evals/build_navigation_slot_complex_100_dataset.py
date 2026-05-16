from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT = Path("evals/datasets/navigation_slot_complex_100_cases.json")

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

GPS_CONTEXT = {
    "current_position": {"latitude": 39.9163, "longitude": 116.3972},
    "current_stop_name": "Forbidden City",
    "next_stop_name": "Jingshan Park",
    "city_code": "beijing",
}
ROUTE_CONTEXT = {
    "current_stop_name": "Forbidden City",
    "next_stop_name": "Jingshan Park",
    "city_code": "beijing",
}


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

    next_stop_templates = [
        "故宫好美啊，我们刚在午门那边拍完照也休息了一下，下一站怎么走？",
        "刚才这段讲解挺有意思，老人也坐了一会儿，现在体力还行，下一站怎么去？",
        "我已经从展厅出来了，孩子还想继续往前逛，接下来怎么走比较省心？",
        "这里人有点多但还能接受，我们先不改路线，接下来怎么去下一站？",
        "拍照结束了，水也买好了，不用讲历史了，去下一站怎么走？",
    ]
    for index in range(20):
        with_gps = index < 12
        context = {**ROUTE_CONTEXT}
        if with_gps:
            context["current_position"] = {"latitude": 39.9163 + index * 0.00005, "longitude": 116.3972}
        cases.append(
            navigation_case(
                f"NAVC-NS-{index + 1:03d}",
                "complex_next_stop",
                next_stop_templates[index % len(next_stop_templates)],
                request_kind="next_stop",
                origin="当前位置" if with_gps else "Forbidden City",
                destinations=["Jingshan Park"],
                session_context=context,
                origin_place_id="gps_current_position" if with_gps else "forbidden_city",
                notes="混入游览反馈/体力/否定改路线后，仍是下一站导航。",
            )
        )

    destination_templates = [
        "故宫确实很好看，我们不想在这里继续停太久了，等会想去{zh}，从我这儿怎么走？",
        "刚才拍照花了点时间，下面准备去{zh}，麻烦给我一段文字路线，不要讲背景。",
        "孩子有点累但还想看下一个点，我想去{zh}，怎么走比较直接？",
        "先不查开放时间，也不用推荐别的景点，导航到{zh}入口怎么走？",
        "我们在附近喝完水了，接着去{zh}怎么走，尽量说清楚步行方向。",
    ]
    for index in range(20):
        canonical, zh, _ = PLACES[(index + 2) % len(PLACES)]
        cases.append(
            navigation_case(
                f"NAVC-DGPS-{index + 1:03d}",
                "complex_destination_gps",
                destination_templates[index % len(destination_templates)].format(zh=zh),
                request_kind="destination_only",
                origin="当前位置",
                destinations=[canonical],
                session_context={**GPS_CONTEXT},
                origin_place_id="gps_current_position",
                notes="混合闲聊后的目的地型导航，GPS 起点优先。",
            )
        )

    current_stop_templates = [
        "刚才在故宫这一段看得挺慢，现在手机定位不太准，但我还在当前站，想去{zh}怎么走？",
        "我不想改行程，只是想从现在这个站继续过去，下面到{zh}怎么去？",
        "这里信号一般，先按我当前站点算，等会去{zh}怎么走，给文字步骤就行。",
        "别推荐路线替换方案，我还是照原计划走，接着去{zh}怎么走？",
        "已经逛完这一站了，想直接去{zh}，怎么走比较清楚？",
    ]
    for index in range(10):
        canonical, zh, _ = PLACES[(index + 4) % len(PLACES)]
        cases.append(
            navigation_case(
                f"NAVC-DCTX-{index + 1:03d}",
                "complex_destination_current_stop",
                current_stop_templates[index % len(current_stop_templates)].format(zh=zh),
                request_kind="destination_only",
                origin="Forbidden City",
                destinations=[canonical],
                session_context={**ROUTE_CONTEXT},
                origin_place_id="forbidden_city",
                notes="无 GPS 时用 current_stop 作为 destination-only 起点。",
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
        "我们上午时间有点赶，但这段还是想自己走，请告诉我从{a}到{b}怎么走？",
        "不用考虑我现在定位，我问的是两个点之间的路，从{a}怎么走到{b}？",
        "如果只看这两个景点之间的步行路线，从{a}前往{b}怎么走？",
        "先不讲{a}和{b}的历史关系，给我从{a}到{b}的文字路线。",
        "我在整理明天路线，想提前确认一下，从{a}到{b}怎么走比较直观？",
    ]
    for index in range(15):
        origin, destination = route_pairs[index % len(route_pairs)]
        origin_zh, origin_id = PLACE_BY_CANONICAL[origin]
        destination_zh, _ = PLACE_BY_CANONICAL[destination]
        cases.append(
            navigation_case(
                f"NAVC-EXP-{index + 1:03d}",
                "complex_explicit_route",
                explicit_templates[index % len(explicit_templates)].format(a=origin_zh, b=destination_zh),
                request_kind="explicit_route",
                origin=origin,
                destinations=[destination],
                session_context={"city_code": "beijing", "current_position": {"latitude": 39.9, "longitude": 116.39}},
                origin_place_id=origin_id,
                notes="显式起终点不受当前 GPS 覆盖。",
            )
        )

    multi_routes = [
        ("Tiananmen Square", ["Forbidden City", "Jingshan Park"]),
        ("Temple of Heaven", ["Zhengyangmen", "Tiananmen Square"]),
        ("Beihai Park", ["Shichahai", "Nanluoguxiang", "Yonghe Temple"]),
        ("Summer Palace", ["Yuanmingyuan Park", "Beihai Park"]),
        ("Prince Gong's Mansion", ["Beihai Park", "Jingshan Park", "Forbidden City"]),
    ]
    multi_templates = [
        "我想把这几段路先看清楚，不是要改路线：从{a}到{b}再到{c}怎么走？",
        "明天可能带父母走这一串点，先确认文字路线，从{a}到{b}再去{c}怎么走？",
        "我们想少走冤枉路，但顺序先不变，从{a}到{b}再到{c}给我分段路线。",
        "不用讲每个景点故事，单纯看路，从{a}到{b}再到{c}怎么走比较清楚？",
    ]
    for index in range(20):
        origin, destinations = multi_routes[index % len(multi_routes)]
        origin_zh, origin_id = PLACE_BY_CANONICAL[origin]
        destination_names = [PLACE_BY_CANONICAL[destination][0] for destination in destinations]
        b = destination_names[0]
        c = "再到".join(destination_names[1:])
        cases.append(
            navigation_case(
                f"NAVC-MULTI-{index + 1:03d}",
                "complex_multi_leg",
                multi_templates[index % len(multi_templates)].format(a=origin_zh, b=b, c=c),
                request_kind="multi_leg",
                origin=origin,
                destinations=destinations,
                session_context={"city_code": "beijing"},
                origin_place_id=origin_id,
                notes="复杂前缀与否定改路线后的多段导航。",
            )
        )

    current_location_templates = [
        "我从故宫出来以后有点分不清方向，现在就按手机定位算，从这里到景山怎么走？",
        "我们站在路边等家人，别按当前站名字估算了，从我这儿到天坛怎么走？",
        "刚出门口，地图上定位已经有了，想从当前位置到正阳门，怎么走？",
        "我不确定自己在景区哪个门，但 GPS 应该是准的，从这里到北海公园怎么走？",
        "拍完照以后方向感有点乱，直接用我这儿的位置，去南锣鼓巷怎么走？",
    ]
    destinations = ["Jingshan Park", "Temple of Heaven", "Zhengyangmen", "Beihai Park", "Nanluoguxiang"]
    for index in range(5):
        cases.append(
            navigation_case(
                f"NAVC-GPS-{index + 1:03d}",
                "complex_current_location",
                current_location_templates[index % len(current_location_templates)],
                request_kind="explicit_route" if index % 5 in {0, 1, 2, 3} else "destination_only",
                origin="当前位置",
                destinations=[destinations[index % len(destinations)]],
                session_context={**GPS_CONTEXT},
                origin_place_id="gps_current_position",
                notes="这里/我这儿/当前位置 应解析为 GPS origin。",
            )
        )

    boundary_cases = [
        ("故宫好美啊，我们刚拍完照也休息了一下，下面要去哪里比较顺？不用给我具体怎么走。", "trip_assistant", "问下一步安排，不是要导航步骤。"),
        ("天坛这段比想象中大，老人有点累，下面去哪会轻松一点？先别给路线。", "trip_assistant", "行程策略问法。"),
        ("景山看完夕阳挺值的，后面要不要还去北海公园？先帮我判断顺不顺。", "trip_assistant", "问是否顺路，不是导航。"),
        ("我觉得今天走太多了，把后面路线改轻松一点，别直接给我导航。", "manual_route_edit_redirect", "明确改路线。"),
        ("孩子累了，把雍和宫删掉或者换成近一点的点吧，不是问怎么走。", "manual_route_edit_redirect", "删点/换点。"),
        ("故宫附近现在堵不堵，我想判断打车会不会很慢。", "out_of_scope", "泛交通拥堵边界。"),
        ("正阳门讲得挺有意思，能不能顺便讲讲它和前门名字的关系？", "attraction_explain", "景点解释，不是导航。"),
        ("刚才那段路线说清楚了，谢谢，先不用继续导航。", "smalltalk", "结束/感谢。"),
        ("帮我把'How do I get to the north gate?'翻成中文给工作人员看，不是真的要导航。", "translation", "显式翻译优先。"),
    ]
    for index, (query, expected_intent, notes) in enumerate(boundary_cases, 1):
        cases.append(boundary_case(f"NAVC-BND-{index:03d}", "complex_boundary_negative", query, expected_intent, notes))
    cases.append(
        navigation_case(
            "NAVC-BND-010",
            "complex_boundary_negative",
            "如果从故宫到天坛坐地铁，具体几号线换乘？我不是问步行路线。",
            request_kind="explicit_route",
            origin="Forbidden City",
            destinations=["Temple of Heaven"],
            session_context=ROUTE_CONTEXT,
            origin_place_id="forbidden_city",
            expected_mode="transit",
            notes="公交/地铁换乘已支持，且否定的是步行路线，不应拒答。",
        )
    )

    assert len(cases) == 100
    return cases


def main() -> None:
    payload = {
        "dataset_name": "navigation_slot_complex_100_cases",
        "dataset_version": "2026-05-15",
        "notes": "Complex mixed-utterance navigation slot benchmark with scenic comments, chatter, long contexts, GPS/current-stop origins, multi-leg routes, and boundary negatives.",
        "cases": build_cases(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(payload['cases'])} cases to {OUT}")


if __name__ == "__main__":
    main()
