from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


OUT = Path("evals/datasets/routing_rule_hard_500_cases.yaml")

INTENT_PREFIX = {
    "smalltalk": "ST",
    "attraction_explain": "AT",
    "live_info": "LI",
    "weather_info": "WE",
    "navigation_text": "NAV",
    "trip_assistant": "TRIP",
    "manual_route_edit_redirect": "EDIT",
    "translation": "TRANS",
    "out_of_scope": "OOS",
}


def case(
    intent: str,
    index: int,
    query: str,
    *,
    bucket: str,
    expected_needs_fallback: bool,
    conflict_type: str,
    label_rationale: str,
    raw_query: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "case_id": f"RRH-{INTENT_PREFIX[intent]}-{index:03d}",
        "bucket": bucket,
        "language": "zh",
        "query": query,
        "expected_intent": intent,
        "expected_needs_fallback": expected_needs_fallback,
        "conflict_type": conflict_type,
        "label_rationale": label_rationale,
    }
    if raw_query:
        item["raw_query"] = raw_query
    if history:
        item["history"] = history
    return item


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    smalltalk_queries = [
        ("你好，我刚打开这个导游助手，先说说你能帮我做什么，不用进入具体景点。", False, "smalltalk_capability"),
        ("你是谁，是人工导游还是智能助手？先回答身份就行。", False, "smalltalk_identity"),
        ("谢谢，刚才那个解释够清楚了，先不用继续推荐路线。", False, "smalltalk_thanks"),
        ("辛苦了，我现在没有新的问题，等到景点门口再问你。", False, "smalltalk_close"),
        ("你好，别急着查天气，我只是想知道你这个助手能不能记住我的行程。", True, "smalltalk_capability_vs_trip"),
        ("你能做什么？比如讲景点、查天气、翻译这些是不是都能处理？", True, "smalltalk_capability_with_intent_words"),
        ("您好，先别讲故宫历史，简单介绍一下你的能力范围。", True, "smalltalk_vs_explain_negated"),
        ("谢谢你，路线先不用改，我只是确认你还在线吗？", True, "smalltalk_vs_edit_negated"),
        ("hello，先不用翻译，告诉我你是不是北京旅游助手。", False, "pivot_smalltalk"),
        ("hi，我只是打个招呼，等会再问故宫怎么走。", True, "smalltalk_future_task"),
        ("麻烦问一下，你能不能只回答北京旅游问题？", False, "smalltalk_domain_capability"),
        ("早上好，今天先从哪里开始我等会再说。", True, "smalltalk_future_trip"),
        ("你是不是可以帮我做文字导航和景点讲解？先回答能做什么。", True, "smalltalk_capability_with_task_words"),
        ("不用安排、不用查票，先告诉我你会不会说中文。", False, "smalltalk_capability_negated_tasks"),
        ("hey, what can you do for a Beijing visitor?", False, "pivot_smalltalk"),
        ("你好，刚才谢谢，暂时别继续输出了。", False, "smalltalk_stop"),
        ("我现在只是测试一下，你收到消息了吗？", False, "smalltalk_status"),
        ("谢谢，先到这里，别再给我推荐景点。", False, "smalltalk_stop_negated_task"),
        ("你能不能简单说一句你支持哪些功能？别举太多例子。", False, "smalltalk_capability"),
        ("您好，如果我问股票你会拒绝吗？我只是问你的边界。", True, "smalltalk_boundary_capability"),
        ("先别执行任何旅游任务，我只想确认你是不是在线。", False, "smalltalk_status"),
        ("多谢，等我到了天坛再问你。", True, "smalltalk_future_place"),
        ("哈喽，不问路线不问天气，就打个招呼。", False, "smalltalk_negated_tasks"),
        ("你能不能后面都用中文回答？这是偏好设置不是翻译。", True, "smalltalk_vs_translation"),
        ("请问你是负责北京游览问答的吗？", False, "smalltalk_identity"),
    ]
    for i, (query, fallback, conflict) in enumerate(smalltalk_queries, 1):
        cases.append(
            case(
                "smalltalk",
                i,
                query,
                bucket="hard_smalltalk",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale="寒暄、身份或能力边界问题，没有当前下游任务。",
                raw_query=query if query.isascii() else None,
            )
        )

    attractions = [
        "故宫",
        "天坛",
        "景山",
        "正阳门",
        "天安门",
        "颐和园",
        "圆明园",
        "北海公园",
        "什刹海",
        "南锣鼓巷",
        "雍和宫",
        "恭王府",
        "故宫博物院",
        "祈年殿",
        "前门",
    ]
    explain_templates = [
        ("我不是问怎么走，也不是问今天开不开，单纯想听听{place}最值得理解的历史线索。", False, "route_live_negated_vs_explain"),
        ("如果只用游客能听懂的话讲，{place}到底特别在哪里，别给我百科清单。", False, "colloquial_explain"),
        ("我已经买好票了，先别查门票，讲讲{place}为什么值得专门停下来听。", False, "live_negated_vs_explain"),
        ("天气等会再说，你先解释{place}的建筑或空间为什么让人有感觉。", False, "weather_negated_vs_explain"),
        ("我不是要翻译英文牌子，想知道{place}相关的这个历史概念到底意味着什么。", False, "translation_negated_vs_explain"),
        ("如果带父母去{place}，有什么故事能讲得不枯燥？", False, "family_explain"),
        ("先不要替我排路线，比较一下{place}和故宫的看点差异。", True, "compare_explain_vs_trip"),
        ("我只有十分钟，{place}最不该错过的理解重点是什么？", False, "time_constraint_explain"),
        ("等下再告诉我导航，现在先讲{place}和北京中轴线有什么关系。", False, "navigation_deferred_vs_explain"),
        ("不要查人多不多，我想知道{place}为什么会给人很强的历史现场感。", False, "crowd_negated_vs_explain"),
        ("{place}如果已经商业化了，它原来的城市格局还有什么可讲？", False, "commercialized_explain"),
        ("请用两段话解释{place}的象征意义，不要进入实时信息。", False, "symbolism_explain"),
        ("我不是要你推荐别的景点，先把{place}这一处讲透。", False, "recommendation_negated_vs_explain"),
        ("{place}适合第一次来北京的人听哪条故事线？", False, "first_time_explain"),
    ]
    for i in range(70):
        place = attractions[i % len(attractions)]
        template, fallback, conflict = explain_templates[i % len(explain_templates)]
        raw_query = None
        if i in {9, 19, 29, 39, 49, 59, 69}:
            raw_query = f"Explain why {place} matters, but do not change my route."
        cases.append(
            case(
                "attraction_explain",
                i + 1,
                template.format(place=place),
                bucket="hard_attraction_explain",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale="核心诉求是景点历史、意义、看点或故事解释。",
                raw_query=raw_query,
            )
        )

    live_templates = [
        ("我已经到{place}门口了，现在还能进去吗，还是今天已经停止入场？", False, "live_entry"),
        ("{place}今天下午还能买票吗，还是必须提前预约？", False, "live_ticket"),
        ("先别讲历史，帮我确认{place}今天有没有闭馆或临时公告。", False, "explain_negated_vs_live"),
        ("{place}今天几点停止检票？我怕赶过去来不及。", False, "live_hours"),
        ("如果{place}今晚开放到比较晚，我再问怎么走；你先查开放信息。", True, "live_primary_navigation_secondary"),
        ("不是问人多不多，只想知道{place}现在还能不能正常参观。", False, "crowd_negated_vs_live"),
        ("{place}今天开不开、门票和预约这几个信息先帮我确认。", False, "multiple_live_operations"),
        ("我不是要翻译“{place}今天开放吗”，是真的想确认它今天开不开。", True, "translation_negated_vs_live"),
        ("{place}今天如果临时维修或者封闭，有没有官方通知？", False, "live_notice"),
        ("先别导航，确认一下{place}这会儿还允许入园吗。", False, "navigation_negated_vs_live"),
        ("{place}下午四点之后还能不能进去参观？", False, "time_entry_status"),
        ("如果{place}今天停售票，就不用继续讲路线；先查票务。", True, "live_condition"),
        ("{place}今天开放吗？如果开放再简单说说为什么值得看。", True, "live_primary_explain_secondary"),
    ]
    for i in range(65):
        place = attractions[i % len(attractions)]
        template, fallback, conflict = live_templates[i % len(live_templates)]
        raw_query = None
        if i in {8, 18, 28, 38, 48, 58}:
            raw_query = f"Is {place} still allowing entry today?"
        cases.append(
            case(
                "live_info",
                i + 1,
                template.format(place=place),
                bucket="hard_live_info",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale="核心诉求是当天官方运营、开放、票务、预约或临时公告。",
                raw_query=raw_query,
            )
        )

    weather_templates = [
        ("去{place}之前要不要带伞？我不是问路线。", False, "weather_umbrella"),
        ("{place}今天下午会不会太晒太热，老人会不会受不了？", False, "weather_heat"),
        ("{place}这会儿冷不冷，穿短袖会不会不合适？", False, "weather_temperature"),
        ("门票我已经买好了，帮我看{place}附近今天会不会下雨。", False, "live_negated_vs_weather"),
        ("{place}今天适合带孩子去吗？主要担心天气和体感。", True, "weather_suitability"),
        ("如果明天下雨，{place}还适不适合安排？先判断天气。", True, "weather_vs_trip"),
        ("不是问空气质量，单纯问{place}今天有没有雨。", False, "air_quality_negated_vs_weather"),
        ("{place}晚上风会不会很大，适不适合散步？", True, "weather_suitability"),
        ("先别查开放时间，我问的是{place}现在温度大概多少。", False, "live_negated_vs_weather"),
        ("从{place}走到景山之前，看看今天会不会下雨。", False, "navigation_context_weather"),
        ("{place}附近体感怎么样，老人需要多穿一件吗？", False, "weather_feels_like"),
        ("今天北京会不会有阵雨，会影响去{place}吗？", True, "weather_trip_decision"),
    ]
    for i in range(60):
        place = attractions[i % len(attractions)]
        template, fallback, conflict = weather_templates[i % len(weather_templates)]
        raw_query = None
        if i in {7, 17, 27, 37, 47, 57}:
            raw_query = f"Will it rain near {place} this afternoon?"
        cases.append(
            case(
                "weather_info",
                i + 1,
                template.format(place=place),
                bucket="hard_weather_info",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale="核心诉求是天气、温度、降雨、体感或带伞判断。",
                raw_query=raw_query,
            )
        )

    nav_pairs = [
        ("天安门", "故宫"),
        ("故宫", "景山"),
        ("天坛", "前门"),
        ("北海公园", "什刹海"),
        ("南锣鼓巷", "雍和宫"),
        ("恭王府", "北海公园"),
        ("正阳门", "天安门广场"),
        ("颐和园", "圆明园"),
    ]
    nav_templates = [
        ("从{origin}到{dest}给我文字路线，不要讲历史。", False, "explicit_route"),
        ("我不坐地铁，从{origin}走到{dest}大概怎么走？", False, "transit_negated_navigation"),
        ("{origin}附近交通路线怎么走？我不是问堵不堵，是问去{dest}的方向。", False, "traffic_word_navigation"),
        ("先不管人多不多，告诉我从{origin}到{dest}入口怎么走。", False, "crowd_negated_navigation"),
        ("如果下雨也没关系，从{origin}到{dest}有没有少绕路的走法？", False, "weather_context_navigation"),
        ("下一站如果还是按原计划走，我现在应该往哪边走？", True, "next_stop_navigation"),
        ("路线别重排，按当前顺序告诉我接下来怎么走。", True, "edit_negated_navigation"),
        ("{origin}到{dest}这段有没有顺路能看的点？先按路线说，不展开历史。", True, "navigation_vs_explain"),
        ("去{dest}怎么走？我在{origin}附近绕晕了。", False, "destination_navigation"),
        ("从{origin}到{dest}再到景山，分两段说文字步骤。", False, "multi_leg_navigation"),
        ("{origin}到{dest}如果打车会不会堵先不问，步行路线说一下。", False, "traffic_negated_navigation"),
        ("如何到达{dest}南门？我只要方向和大概路径。", False, "destination_navigation"),
        ("如果{dest}还开门就导航过去；先按能去的情况给我路线。", True, "live_condition_navigation"),
    ]
    for i in range(65):
        origin, dest = nav_pairs[i % len(nav_pairs)]
        template, fallback, conflict = nav_templates[i % len(nav_templates)]
        raw_query = None
        if i in {6, 16, 26, 36, 46, 56}:
            raw_query = f"Give me walking directions from {origin} to {dest}, not history."
        cases.append(
            case(
                "navigation_text",
                i + 1,
                template.format(origin=origin, dest=dest),
                bucket="hard_navigation_text",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale="核心诉求是文字导航、路线步骤、目的地或多段路线。",
                raw_query=raw_query,
            )
        )

    trip_templates = [
        ("我刚从{place}出来，先别导航，告诉我按现在行程下一站应该去哪。", True, "session_next_stop"),
        ("当前路线走到哪里了，后面还剩几个点？", True, "trip_status"),
        ("别改路线，我只是想知道下一站是不是{place}。", True, "edit_negated_trip"),
        ("今天路线不用改，帮我看还剩哪些点没去。", True, "trip_remaining"),
        ("后面先看哪个点比较顺？先给建议，不要直接替我改。", True, "trip_advice_vs_edit"),
        ("如果下午下雨，后面行程怎么安排比较稳？", True, "weather_condition_trip"),
        ("天坛开不开先不查，按原计划它是不是后面的点？", True, "live_negated_trip"),
        ("刚才说的下一站我忘了，你再提醒一下，不要开始导航。", True, "navigation_negated_trip"),
        ("老人有点累，后面行程是不是该放慢一点？先别改路线。", True, "soft_edit_negated_trip"),
        ("下一站如果是{place}，先确认一下，不要展开讲它的历史。", True, "trip_primary_explain_negated"),
        ("现在这个行程顺不顺？不需要你改，只评价一下。", True, "trip_advice"),
        ("今天剩下的点里，哪个最值得保留？先给判断，不要直接删除。", True, "trip_advice_vs_edit"),
        ("接下来是先吃饭还是先看下一个景点更合理？不是餐厅推荐。", True, "food_boundary_trip"),
    ]
    for i in range(65):
        place = attractions[i % len(attractions)]
        template, fallback, conflict = trip_templates[i % len(trip_templates)]
        raw_query = None
        if i in {5, 15, 25, 35, 45, 55}:
            raw_query = "Where are we in the itinerary now, not directions yet."
        history = None
        if i % 5 == 0:
            history = [{"intent": "trip_assistant", "content": "当前行程包含故宫、景山和天坛。"}]
        cases.append(
            case(
                "trip_assistant",
                i + 1,
                template.format(place=place),
                bucket="hard_trip_assistant",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale="核心诉求是当前行程状态、下一站、剩余站点或行程建议。",
                raw_query=raw_query,
                history=history,
            )
        )

    edit_templates = [
        ("我临时不想去{place}了，帮我从今天路线里删掉，别只是建议。", "manual_route_edit_redirect", False, "explicit_remove"),
        ("把{place}提前到上午，这个顺序帮我改一下。", "manual_route_edit_redirect", False, "explicit_reorder"),
        ("{place}能不能放到最后？我想先走市中心几个点。", "manual_route_edit_redirect", False, "explicit_reorder"),
        ("把{place}换成北海公园吧，我想看更有故事的院子。", "manual_route_edit_redirect", False, "explicit_replace"),
        ("今天老人累了，把路线改轻松一点，少走台阶和回头路。", "manual_route_edit_redirect", False, "explicit_soft_edit"),
        ("这条行程太赶，帮我压缩成少一点景点，不要只是口头建议。", "manual_route_edit_redirect", False, "explicit_soft_edit"),
        ("如果{place}今天买不到票，就把它换成景山。", "manual_route_edit_redirect", True, "conditional_live_edit"),
        ("如果下午下雨，就把室外的{place}挪到明天。", "manual_route_edit_redirect", True, "conditional_weather_edit"),
        ("不要直接删{place}，先告诉我删掉之后路线会不会更轻松。", "trip_assistant", True, "edit_negated_trip_advice"),
        ("我不是要你改路线，只是问如果少去一个点哪个最合适。", "trip_assistant", True, "edit_negated_trip_advice"),
        ("先别改路线，从{place}到景山怎么走？", "navigation_text", False, "edit_negated_navigation"),
        ("不要调整{place}顺序，我只是想知道它为什么值得去。", "attraction_explain", False, "edit_negated_explain"),
        ("餐厅不用推荐，但路线中午能不能留一点吃饭时间？", "manual_route_edit_redirect", True, "restaurant_negated_edit"),
        ("把{place}去掉，天坛提前，剩下的别动。", "manual_route_edit_redirect", False, "multi_action_edit"),
    ]
    for i in range(55):
        place = attractions[i % len(attractions)]
        template, expected_intent, fallback, conflict = edit_templates[i % len(edit_templates)]
        raw_query = None
        if i in {4, 14, 24, 34, 44, 54}:
            raw_query = f"Remove {place} from today's itinerary, don't just explain it."
        cases.append(
            case(
                expected_intent,
                i + 1,
                template.format(place=place),
                bucket="hard_manual_route_edit"
                if expected_intent == "manual_route_edit_redirect"
                else "hard_route_edit_negative",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale="根据否定词和动作判定，不把所有含路线词的句子都标成编辑。",
                raw_query=raw_query,
            )
        )

    translation_templates = [
        ("把“Where is the nearest entrance?”翻成中文给工作人员看，别回答入口在哪。", "translation", False, "translation_vs_navigation"),
        ("请把“Is the museum still open today?”翻成中文，不要真的去查开放时间。", "translation", False, "translation_vs_live"),
        ("这句怎么用中文说：Could you help me find my family?", "translation", False, "explicit_translation_text"),
        ("帮我把这句话翻给检票口工作人员看：I bought the ticket online.", "translation", False, "show_staff"),
        ("把“请问卫生间在哪里”做成中英双语展示，我要直接拿给人看。", "translation", False, "bilingual"),
        ("用中文介绍故宫的历史，不是把外语翻成中文。", "attraction_explain", False, "translation_negated_explain"),
        ("讲讲英文牌子里说的 Imperial Garden 是什么地方，我不是要逐句翻译。", "attraction_explain", False, "translation_negated_explain"),
        ("请用中文回答故宫今天开不开，不是翻译这句话。", "live_info", True, "translation_negated_live"),
        ("帮我翻译“Can you remove Jingshan from the route?”这句话，不要改我的路线。", "translation", False, "translation_vs_edit"),
        ("给本地人看的话怎么说：我们想从这里去故宫入口。", "translation", False, "show_local"),
        ("翻译介绍故宫这几个字是什么意思？", "translation", True, "ambiguous_translation_explain"),
        ("能不能用中文给外国朋友介绍天坛？", "attraction_explain", True, "ambiguous_translation_explain"),
        ("把“今天会不会下雨”翻成中文给司机看，不用真的查天气。", "translation", False, "translation_vs_weather"),
        ("这段话双语显示：我和家人走散了，请帮我联系工作人员。", "translation", False, "bilingual"),
        ("请翻成中文：I cannot find the exit near the north gate.", "translation", False, "pivot_translation"),
    ]
    for i in range(45):
        template, expected_intent, fallback, conflict = translation_templates[i % len(translation_templates)]
        raw_query = None
        if i in {6, 16, 26, 36}:
            raw_query = "Translate for staff: I cannot find the exit."
        cases.append(
            case(
                expected_intent,
                i + 1,
                template,
                bucket="hard_translation"
                if expected_intent == "translation"
                else "hard_translation_negative",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale="根据是否有待翻译文本和否定词区分翻译、讲解和 live 查询。",
                raw_query=raw_query,
            )
        )

    oos_templates = [
        ("我知道你是导游，但顺便帮我写一段 Python 抢票脚本吧。", "hard_deny_code"),
        ("旅游先放一边，帮我分析一下这只股票明天能不能买。", "hard_deny_finance"),
        ("我在景区头疼，直接告诉我该吃多少药。", "hard_deny_medical"),
        ("帮我写一份起诉景区的法律文书，越正式越好。", "hard_deny_legal"),
        ("故宫现在排队到底多久？我不是问开放时间，就问队伍长不长。", "unsupported_crowd"),
        ("天坛这会儿人多不多，会不会挤到老人走不动？", "unsupported_crowd"),
        ("故宫周边现在堵车吗？我想判断打车会不会卡住。", "unsupported_traffic"),
        ("从酒店去天坛坐公交还是地铁，具体几号线换乘？", "unsupported_transit"),
        ("颐和园附近停车场还有没有空位，价格大概多少？", "unsupported_parking"),
        ("故宫附近有没有适合带孩子吃饭的餐厅，最好别太贵。", "unsupported_restaurant"),
        ("今天北京 PM2.5 高不高，适不适合老人户外走一天？", "unsupported_air_quality"),
        ("故宫为什么总让人觉得人很渺小？这里的人不是指人多。", "boundary_negative_explain"),
        ("天坛的回音壁是不是和空气质量没关系？我想听建筑原理。", "boundary_negative_explain"),
        ("如果故宫今天不开，你能不能顺便帮我规划一套股票投资路线？", "hard_deny_mixed_live"),
        ("Can you write JavaScript code for my travel website?", "pivot_hard_deny_code"),
    ]
    for i in range(50):
        query, conflict = oos_templates[i % len(oos_templates)]
        expected = "out_of_scope"
        fallback = False
        rationale = "域外 hard deny 或当前不支持的实时边界。"
        if conflict == "boundary_negative_explain":
            expected = "attraction_explain"
            rationale = "边界词被否定，实际是景点讲解。"
        cases.append(
            case(
                expected,
                i + 1 if expected == "out_of_scope" else 71 + i,
                query,
                bucket="hard_out_of_scope" if expected == "out_of_scope" else "hard_boundary_negative",
                expected_needs_fallback=fallback,
                conflict_type=conflict,
                label_rationale=rationale,
                raw_query=query if query.isascii() else None,
            )
        )

    return cases


def main() -> None:
    cases = build_cases()
    if len(cases) != 500:
        raise RuntimeError(f"expected 500 cases, got {len(cases)}")
    counters: dict[str, int] = {}
    for item in cases:
        intent = str(item["expected_intent"])
        counters[intent] = counters.get(intent, 0) + 1
        item["case_id"] = f"RRH-{INTENT_PREFIX[intent]}-{counters[intent]:03d}"
    case_ids = [item["case_id"] for item in cases]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicates:
        raise RuntimeError(f"duplicate case ids: {duplicates[:10]}")

    payload = {
        "dataset_name": "routing_rule_hard_500_cases",
        "dataset_version": "2026-05-15",
        "notes": (
            "500 hard cases for QA intent routing. Queries are Chinese canonical "
            "forms after translator pivot; raw_query is retained on selected "
            "multilingual examples for traceability."
        ),
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
