from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUTPUT = Path("evals/datasets/e2e_qa_intent_hard_1800_cases.json")
INTENT_TOTAL = 200

SQL_ATTRACTIONS = ["故宫", "天坛", "景山公园", "颐和园", "天安门"]
LIVE_ATTRACTIONS = ["故宫", "天坛", "景山公园", "颐和园", "天安门"]
OUTSIDE_SQL_ATTRACTIONS = [
    "鸟巢",
    "国家博物馆",
    "八达岭长城",
    "慕田峪长城",
    "水立方",
    "798艺术区",
    "北海公园",
    "恭王府",
    "正阳门",
    "雍和宫",
    "孔庙",
    "国子监",
]
NAV_PLACES = ["天安门", "故宫", "景山公园", "北海公园", "恭王府", "什刹海", "南锣鼓巷", "雍和宫", "天坛", "颐和园"]
PROFILE_IDS = [
    "bench-user-history-zh",
    "bench-user-family-zh",
    "bench-user-photo-zh",
    "bench-user-story-architecture-zh",
    "bench-user-route-walk-zh",
    "bench-user-history-en",
    "bench-user-family-en",
    "bench-user-active-view-en",
]
SEA_LANGUAGES = ["th", "vi", "id", "ms", "fil", "my", "km", "lo"]


def main() -> None:
    cases: list[dict[str, Any]] = []
    builders = [
        build_smalltalk_case,
        build_out_of_scope_case,
        build_attraction_case,
        build_live_info_case,
        build_weather_case,
        build_navigation_case,
        build_trip_case,
        build_manual_route_edit_case,
        build_translation_case,
    ]
    for builder in builders:
        for index in range(1, INTENT_TOTAL + 1):
            cases.append(builder(index))

    payload = {
        "dataset_name": "e2e_qa_intent_hard",
        "dataset_version": "2026-05-16-v1",
        "description": (
            "Full-chain QA hard benchmark: 200 cases per supported intent. "
            "Queries mix zh/en/Southeast Asian languages, long oral phrasing, "
            "multi-intent distractors, mock-SQL grounding, RAG deep questions, "
            "model-knowledge gaps, provider-backed live/weather/navigation, "
            "session-aware trip assistance, route-edit redirects, and final answer checks."
        ),
        "cases": cases,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT} cases={len(cases)}")


def build_smalltalk_case(index: int) -> dict[str, Any]:
    templates = [
        "你好，先不用讲景点，我只是想确认你是不是北京导游助手。",
        "你能做什么？请只说能力边界，不要顺便推荐具体路线。",
        "谢谢你，刚才的建议我看到了，先不用继续查开放时间。",
        "早上好，我等朋友集合，先问一下你能不能陪我做讲解。",
        "如果我后面问故宫历史、导航和天气，你分别能怎么帮我？",
        "你是人工客服还是智能导游？不要开始介绍任何景点。",
        "先打个招呼，等下我再问路线，现在不用操作行程。",
        "我第一次用这个导游，简单说说你会怎么回答问题。",
    ]
    zh_query = with_noise(templates[index % len(templates)], index)
    return make_case(
        index=index,
        intent="smalltalk",
        abbreviation="SMALL",
        zh_query=zh_query,
        operation="smalltalk_capability_boundary",
        expected_data_source="none",
        fixture_mode="none",
        assertions={"must_not_depend_on": ["RAG", "实时搜索", "高德"]},
    )


def build_out_of_scope_case(index: int) -> dict[str, Any]:
    templates = [
        "现在故宫门口排队大概要多久？别讲历史，我只想知道实时拥挤程度。",
        "去天坛路上会不会堵车？如果堵就帮我判断几点出发最好。",
        "帮我写一个 Python 爬虫，把北京景点官网开放时间都抓下来。",
        "今天北京空气质量适不适合带孩子长时间户外走？",
        "故宫附近停车场还有车位吗，能不能直接给我实时车位数？",
        "我想买股票，顺便问下游北京时应该带多少现金。",
        "帮我订两张今晚演出票，最好直接付款。",
        "能不能预测一下明天景山游客会不会爆满？",
    ]
    zh_query = with_noise(templates[index % len(templates)], index)
    return make_case(
        index=index,
        intent="out_of_scope",
        abbreviation="OOS",
        zh_query=zh_query,
        operation="hard_deny_or_boundary_guard",
        expected_data_source="boundary_guard",
        fixture_mode="none",
        assertions={"must_include_any": ["北京旅游", "当前不支持", "无法", "不能"]},
    )


def build_attraction_case(index: int) -> dict[str, Any]:
    bucket = index % 5
    if bucket in {0, 1, 2}:
        attraction = SQL_ATTRACTIONS[index % len(SQL_ATTRACTIONS)]
        templates = [
            "我第一次来北京，{name}适合怎么理解？请用两三段介绍重点。",
            "别查今天开放，我只想听{name}平时参观的历史、看点和注意事项。",
            "带父母去{name}，你用游客能听懂的话讲讲它为什么值得停留。",
            "如果时间不多，{name}有哪些必看的地方和大概停留多久？",
            "请别给路线，单纯讲{name}的背景、亮点和拍照提醒。",
        ]
        operation = "sql_grounded_generation"
        expected_data_source = "sql"
        fixture_mode = "mock_sql_attraction"
    elif bucket == 3:
        attraction = SQL_ATTRACTIONS[index % len(SQL_ATTRACTIONS)]
        templates = [
            "请深入拆解{name}和北京中轴线、空间秩序之间的关系，别只讲门票。",
            "我想听{name}背后的象征意义和建筑秩序，尽量讲出深层历史脉络。",
            "不要泛泛介绍{name}，请展开它在仪式、权力表达和城市秩序里的含义。",
            "从策展和建筑语言角度，{name}为什么能代表老北京的空间叙事？",
        ]
        operation = "sql_then_rag_generation"
        expected_data_source = "sql_then_rag"
        fixture_mode = "mock_sql_plus_rag"
    else:
        attraction = OUTSIDE_SQL_ATTRACTIONS[index % len(OUTSIDE_SQL_ATTRACTIONS)]
        templates = [
            "数据库里可能还没整理{name}，但它也是北京游客会问的点，请先用常识简单介绍。",
            "我临时想了解{name}，不用查实时开放，先讲它的背景和参观价值。",
            "如果后面再补数据，现在先回答{name}是什么、适合谁去、怎么看。",
        ]
        operation = "model_knowledge_gap_generation"
        expected_data_source = "model_knowledge"
        fixture_mode = "outside_mock_sql_beijing_attraction"
    zh_query = with_noise(templates[index % len(templates)].format(name=attraction), index)
    return make_case(
        index=index,
        intent="attraction_explain",
        abbreviation="ATTR",
        zh_query=zh_query,
        operation=operation,
        expected_data_source=expected_data_source,
        profile_id=PROFILE_IDS[index % len(PROFILE_IDS)],
        fixture_mode=fixture_mode,
    )


def build_live_info_case(index: int) -> dict[str, Any]:
    attraction = LIVE_ATTRACTIONS[index % len(LIVE_ATTRACTIONS)]
    templates = [
        "{name}今天开放吗？不要讲历史，只要确认今天能不能去。",
        "现在还能进{name}吗？如果只是数据库里的常规时间也请标明不确定。",
        "{name}今天有没有临时闭馆、预约或公告变化？我准备出门前确认。",
        "帮我查{name}今天最晚几点停止入园，别顺便推荐路线。",
        "我看到网上说{name}可能调整开放，今天到底能不能参观？",
    ]
    zh_query = with_noise(templates[index % len(templates)].format(name=attraction), index)
    return make_case(
        index=index,
        intent="live_info",
        abbreviation="LIVE",
        zh_query=zh_query,
        operation="live_info_provider_or_cache",
        expected_data_source="live_info",
        fixture_mode="live_provider_with_cache",
    )


def build_weather_case(index: int) -> dict[str, Any]:
    location = ["北京", "故宫", "天坛", "景山公园", "颐和园", "北海公园"][index % 6]
    templates = [
        "{name}附近今天会不会下雨？我只问天气，不问开放时间。",
        "下午去{name}会不会太冷或太热，适不适合老人慢慢走？",
        "如果我们傍晚到{name}，现在天气需要带伞吗？",
        "别查排队人数，帮我看{name}当前天气和温度。",
        "今天{name}一带风大不大？我想决定要不要去户外点。",
    ]
    zh_query = with_noise(templates[index % len(templates)].format(name=location), index)
    return make_case(
        index=index,
        intent="weather_info",
        abbreviation="WEATHER",
        zh_query=zh_query,
        operation="weather_provider_lookup",
        expected_data_source="weather",
        fixture_mode="amap_weather",
    )


def build_navigation_case(index: int) -> dict[str, Any]:
    origin = NAV_PLACES[index % len(NAV_PLACES)]
    dest1 = NAV_PLACES[(index + 2) % len(NAV_PLACES)]
    dest2 = NAV_PLACES[(index + 4) % len(NAV_PLACES)]
    kind = index % 5
    if kind == 0:
        zh_query = "刚从展厅出来，老人也休息好了，下一站怎么去？只要文字路线。"
    elif kind == 1:
        zh_query = f"我在这里，接着到{dest1}怎么走？如果不远就步行，别改行程。"
    elif kind == 2:
        zh_query = f"从{origin}到{dest1}怎么走？我想看分步文字导航。"
    elif kind == 3:
        zh_query = f"明天可能带父母走这一串点，从{origin}到{dest1}再到{dest2}怎么走？"
    else:
        mode = ["步行", "坐公交", "坐地铁", "打车"][index % 4]
        zh_query = f"不用讲每个景点历史，从{origin}到{dest1}{mode}怎么走，给我路线就好。"
    context = session_context(index, current=origin, next_stop=dest1)
    return make_case(
        index=index,
        intent="navigation_text",
        abbreviation="NAV",
        zh_query=with_noise(zh_query, index),
        operation="navigation_slot_and_amap_lookup",
        expected_data_source="navigation",
        fixture_mode="session_or_amap_navigation",
        request_context=context,
    )


def build_trip_case(index: int) -> dict[str, Any]:
    current = NAV_PLACES[index % len(NAV_PLACES)]
    next_stop = NAV_PLACES[(index + 1) % len(NAV_PLACES)]
    templates = [
        "我下一站去哪？别开始导航，先告诉我行程状态。",
        "现在到哪一站了？如果还没结束，也说一下后面还有几个点。",
        "老人有点累，但先不要改路线，接下来这个点还适合继续吗？",
        "我们刚看完这里，下面怎么安排比较顺，不要删除任何景点。",
        "如果孩子想休息十分钟，后面节奏怎么把握？先按原计划说。",
    ]
    zh_query = with_noise(templates[index % len(templates)], index)
    return make_case(
        index=index,
        intent="trip_assistant",
        abbreviation="TRIP",
        zh_query=zh_query,
        operation="session_context_trip_generation",
        expected_data_source="session_context",
        profile_id=PROFILE_IDS[index % len(PROFILE_IDS)],
        fixture_mode="session_context",
        request_context=session_context(index, current=current, next_stop=next_stop),
    )


def build_manual_route_edit_case(index: int) -> dict[str, Any]:
    spot = NAV_PLACES[index % len(NAV_PLACES)]
    replacement = NAV_PLACES[(index + 3) % len(NAV_PLACES)]
    templates = [
        "把{spot}从路线里删掉，今天走轻松一点，不是问怎么导航。",
        "下一站别去{spot}了，换成{replacement}，请走路线编辑流程。",
        "把{spot}提前到第一个，后面的顺序重新排一下。",
        "今天不想逛{spot}，帮我改行程，不要只给建议。",
        "如果下雨，就把{spot}挪到明天，今天换一个室内点。",
    ]
    zh_query = with_noise(templates[index % len(templates)].format(spot=spot, replacement=replacement), index)
    return make_case(
        index=index,
        intent="manual_route_edit_redirect",
        abbreviation="EDIT",
        zh_query=zh_query,
        operation="manual_route_edit_redirect",
        expected_data_source="product_redirect",
        profile_id="bench-user-route-walk-zh",
        fixture_mode="session_context",
        request_context=session_context(index, current=spot, next_stop=replacement),
    )


def build_translation_case(index: int) -> dict[str, Any]:
    phrases = [
        "Where is the restroom?",
        "Could you please take a photo for us?",
        "We have already booked tickets online.",
        "Is this entrance for visitors?",
        "Could you help us call a taxi?",
        "Please speak a little slower.",
        "We are looking for the north gate.",
        "Can we store luggage here?",
    ]
    phrase = phrases[index % len(phrases)]
    zh_query = f"帮我把“{phrase}”翻成中文，最好能给工作人员看。"
    lang = language_for(index)
    if lang == "zh":
        query = zh_query
    elif lang == "en":
        query = f'Please translate this into Chinese for local staff: "{phrase}"'
    else:
        query = foreign_prefix(lang) + f' 请翻译给工作人员看：“{phrase}”'
    return make_case(
        index=index,
        intent="translation",
        abbreviation="TRANS",
        zh_query=zh_query,
        operation="explicit_translation_plain_mt",
        expected_data_source="translation",
        fixture_mode="translation_provider",
        language=lang,
        query=query,
    )


def make_case(
    *,
    index: int,
    intent: str,
    abbreviation: str,
    zh_query: str,
    operation: str,
    expected_data_source: str,
    fixture_mode: str,
    profile_id: str | None = None,
    assertions: dict[str, Any] | None = None,
    request_context: dict[str, Any] | None = None,
    language: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    lang = language or language_for(index)
    raw_query = query or localize(zh_query, lang)
    request: dict[str, Any] = {"query": raw_query, "language": lang}
    if request_context:
        request["context"] = request_context
    return {
        "case_id": f"E2EH-{abbreviation}-{index:03d}",
        "category": intent,
        "title": f"{intent} hard case {index:03d}",
        "language": lang,
        "mode": "single_turn_with_context" if request_context else "single_turn",
        "operation": operation,
        "query_zh": zh_query,
        "reality_level": "full_chain",
        "expected_intent": intent,
        "expected_data_source": expected_data_source,
        "session_required": False,
        "profile_id": profile_id,
        "fixture_mode": fixture_mode,
        "variant_group": f"{intent}-hard-200",
        "assertions": assertions or {"check_metadata": ["latency_ms.total_ms"]},
        "request": request,
    }


def language_for(index: int) -> str:
    mod = (index - 1) % 5
    if mod in {0, 1, 2}:
        return "zh"
    if mod == 3:
        return "en"
    return SEA_LANGUAGES[((index - 1) // 5) % len(SEA_LANGUAGES)]


def localize(zh_query: str, language: str) -> str:
    if language == "zh":
        return zh_query
    if language == "en":
        return f"Could you answer this Beijing travel question: {zh_query}"
    return foreign_prefix(language) + zh_query


def foreign_prefix(language: str) -> str:
    return {
        "th": "ช่วยตอบคำถามท่องเที่ยวปักกิ่งนี้: ",
        "vi": "Hãy trả lời câu hỏi du lịch Bắc Kinh này: ",
        "id": "Tolong jawab pertanyaan wisata Beijing ini: ",
        "ms": "Tolong jawab soalan pelancongan Beijing ini: ",
        "fil": "Pakisagot ang tanong sa Beijing trip na ito: ",
        "my": "ဒီ Beijing ခရီးသွားမေးခွန်းကို ဖြေပေးပါ: ",
        "km": "សូមឆ្លើយសំណួរទេសចរណ៍ប៉េកាំងនេះ៖ ",
        "lo": "ຊ່ວຍຕອບຄໍາຖາມທ່ຽວປັກກິ່ງນີ້: ",
    }.get(language, "")


def with_noise(query: str, index: int) -> str:
    prefixes = [
        "",
        "你好，麻烦你看一下，",
        "我们现在有点赶时间，",
        "先别给一大段泛泛建议，",
        "同行里有老人和孩子，",
    ]
    suffixes = [
        "",
        "如果需要取舍，请先按游客最常用的情况回答。",
        "不要把它误当成改路线或闲聊。",
        "我希望回答能直接给同伴看。",
        "能顺便说清楚你依据的是哪类信息最好。",
    ]
    return f"{prefixes[index % len(prefixes)]}{query}{suffixes[(index // 3) % len(suffixes)]}"


def session_context(index: int, *, current: str, next_stop: str) -> dict[str, Any]:
    positions = [
        {"latitude": 39.9050, "longitude": 116.3976},
        {"latitude": 39.9163, "longitude": 116.3972},
        {"latitude": 39.9240, "longitude": 116.3967},
        {"latitude": 39.9996, "longitude": 116.2755},
    ]
    return {
        "qa_playground": {
            "session_override": {
                "city_code": "beijing",
                "current_stop_name": current,
                "next_stop_name": next_stop,
                "current_stop_index": index % 4,
                "stop_count": 5,
                "remaining_stop_count": max(0, 4 - (index % 4)),
                "plan_summary": "北京经典文化动线，含中轴线、皇家园林和胡同街区。",
                "current_position": positions[index % len(positions)],
            }
        }
    }


if __name__ == "__main__":
    main()
