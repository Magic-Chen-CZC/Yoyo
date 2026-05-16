from yoyo.modules.qa.domain_guard import evaluate_domain_support, is_supported_query
from yoyo.modules.qa.intent_router import score_intent
from yoyo.modules.qa.orchestrator import _domain_guard_query
from yoyo.modules.qa.schemas import QAResolvedQuery


def test_domain_guard_accepts_zh_hard_attraction_and_boundary_queries() -> None:
    assert is_supported_query("如果第一次带家人去天坛，不聊路线的话，它最值得看的到底是什么？") is True
    assert is_supported_query("北京今天会不会下雨？") is True
    assert is_supported_query("现在故宫排队大概要多久？") is True


def test_intent_router_prefers_attraction_explain_for_zh_hard_explain_query() -> None:
    result = score_intent("别给我安排路线，直接讲景山最值得看的地方。")
    assert result["intent"] == "attraction_explain"


def test_intent_router_translation_does_not_overcatch_zh_hard_explanation_query() -> None:
    result = score_intent("英文讲解里提到的中轴线，到底是在说什么？")
    assert result["intent"] == "attraction_explain"


def test_intent_router_returns_manual_route_edit_redirect_for_zh_hard_query() -> None:
    result = score_intent("把景山去掉，路线轻松点。")
    assert result["intent"] == "manual_route_edit_redirect"
    assert result["needs_fallback"] is False


def test_intent_router_followup_like_short_query_does_not_direct_hit_trip_assistant() -> None:
    result = score_intent(
        "然后呢？",
        dialogue_history=[{"intent": "trip_assistant", "content": "逛完故宫后先去景山，再往北海走会顺一点。"}],
    )
    assert result["needs_fallback"] is True


def test_intent_router_followup_like_route_edit_query_needs_fallback_without_strong_object_signal() -> None:
    result = score_intent(
        "那把这个删掉吧。",
        dialogue_history=[{"intent": "manual_route_edit_redirect", "content": "我觉得景山那段有点累。"}],
    )
    assert result["needs_fallback"] is True


def test_intent_router_route_edit_negation_keeps_trip_assistant_query_out_of_direct_edit() -> None:
    result = score_intent("先别改路线，只告诉我下一站更推荐去哪。")
    assert result["intent"] == "trip_assistant"
    assert result["needs_fallback"] is False


def test_intent_router_marks_live_vs_explain_conflict_for_zh_hard_case() -> None:
    result = score_intent("故宫今天开放吗，顺便讲讲值不值得去。")
    assert result["intent"] in {"live_info", "attraction_explain"}
    assert result["runner_up_intent"] in {"live_info", "attraction_explain"}
    assert result["needs_fallback"] is True
    assert result["fallback_reason"] == "live_vs_attraction_conflict"


def test_intent_router_translation_beats_other_signals_for_zh_hard_query() -> None:
    result = score_intent("把这句改成中文。")
    assert result["intent"] == "translation"


def test_intent_router_translation_live_mixed_query_goes_fallback() -> None:
    result = score_intent("把今天的闭馆通知翻成中文给工作人员看。")
    assert result["intent"] == "translation"
    assert result["needs_fallback"] is True
    assert result["fallback_reason"] == "translation_live_conflict"


def test_intent_router_translation_handles_show_to_local_phrase_with_quoted_text() -> None:
    result = score_intent("帮我把‘Where is the restroom?’翻给工作人员看")
    assert result["intent"] == "translation"
    assert result["needs_fallback"] is False


def test_intent_router_direct_smalltalk_only_hits_smalltalk_without_fallback() -> None:
    result = score_intent("hello")
    assert result["intent"] == "smalltalk"
    assert result["needs_fallback"] is False


def test_intent_router_smalltalk_with_extra_content_needs_fallback() -> None:
    result = score_intent("你好，请帮我介绍一下北京")
    assert result["intent"] == "smalltalk"
    assert result["needs_fallback"] is True
    assert result["fallback_reason"] == "smalltalk_with_extra_content"


def test_intent_router_partial_english_greeting_no_longer_direct_hits_smalltalk() -> None:
    result = score_intent("How would you explain what makes Shichahai distinctive for a traveler who wants local texture rather than just a famous name?")
    assert result["intent"] != "smalltalk"


def test_intent_router_routes_weather_query_to_weather_info() -> None:
    result = score_intent("北京今天会不会下雨？")
    assert result["intent"] == "weather_info"
    assert result["needs_fallback"] is False


def test_intent_router_routes_temperature_question_to_weather_info() -> None:
    result = score_intent("北京今天大概多少度？")
    assert result["intent"] == "weather_info"
    assert result["needs_fallback"] is False


def test_intent_router_routes_navigation_query_to_navigation_text() -> None:
    result = score_intent("从天安门怎么走到故宫？")
    assert result["intent"] == "navigation_text"
    assert result["needs_fallback"] is False


def test_intent_router_routes_destination_only_navigation_query_to_navigation_text() -> None:
    result = score_intent("去故宫怎么走？")
    assert result["intent"] == "navigation_text"
    assert result["needs_fallback"] is False


def test_intent_router_routes_next_stop_navigation_query_to_navigation_text() -> None:
    result = score_intent("下一站怎么去？")
    assert result["intent"] == "navigation_text"
    assert result["needs_fallback"] is False


def test_intent_router_navigation_negation_keeps_next_stop_destination_as_trip_assistant() -> None:
    result = score_intent("别导航，下一站去哪")
    assert result["intent"] == "trip_assistant"
    assert result["needs_fallback"] is False


def test_intent_router_route_edit_negation_does_not_suppress_navigation_text() -> None:
    result = score_intent("别改路线，从南锣鼓巷到景山怎么走？")
    assert result["intent"] == "navigation_text"
    assert result["needs_fallback"] is False


def test_intent_router_routes_followup_wording_navigation_query_to_navigation_text() -> None:
    result = score_intent("接下来怎么走？")
    assert result["intent"] == "navigation_text"
    assert result["needs_fallback"] is False


def test_intent_router_routes_multi_leg_navigation_query_to_navigation_text() -> None:
    result = score_intent("从天安门到故宫再到景山怎么走？")
    assert result["intent"] == "navigation_text"
    assert result["needs_fallback"] is False


def test_intent_router_queue_query_stays_boundary_out_of_scope() -> None:
    result = score_intent("现在故宫排队大概要多久？")
    assert result["intent"] == "out_of_scope"
    assert result["needs_fallback"] is True
    assert result["fallback_reason"] == "boundary_topic_conflict"
    assert result["boundary_topic"] == "crowd"
    assert result["out_of_scope_subtype"] == "crowd_boundary"


def test_domain_guard_hard_denies_programming_query_in_zh() -> None:
    result = evaluate_domain_support("给我写个 Python 排序算法。")
    assert result.supported is False
    assert result.hard_deny is True
    assert result.deny_reason == "hard_deny_non_travel_domain"


def test_domain_guard_hard_denies_programming_crawler_even_with_opening_hours() -> None:
    result = evaluate_domain_support("帮我写一个 Python 爬虫，把北京景点官网开放时间都抓下来。")
    assert result.supported is False
    assert result.hard_deny is True
    assert result.deny_reason == "hard_deny_non_travel_domain"


def test_domain_guard_query_preserves_raw_hard_deny_signals_after_translation_loss() -> None:
    resolved = QAResolvedQuery(
        raw_query="Hãy trả lời câu hỏi du lịch Bắc Kinh này: 帮我写一个 Python 爬虫，把北京景点官网开放时间都抓下来。",
        effective_query="请回答这个北京旅游的问题：（帮我写一个）。",
        user_language="vi",
        processing_language="zh",
        used_translation_pivot=True,
        pivot_query="请回答这个北京旅游的问题：（帮我写一个）。",
    )
    result = evaluate_domain_support(_domain_guard_query(resolved))
    assert result.supported is False
    assert result.hard_deny is True


def test_domain_guard_keeps_weak_travel_queries_supported_for_router() -> None:
    result = evaluate_domain_support("帮我翻成中文给工作人员看。")
    assert result.supported is True
    assert result.hard_deny is False
    assert result.deny_reason is None


def test_intent_router_trip_assistant_handles_zh_hard_phrase_variant() -> None:
    result = score_intent("故宫之后去哪会比较顺？")
    assert result["intent"] == "trip_assistant"


def test_intent_router_routes_current_stop_status_query_to_trip_assistant() -> None:
    result = score_intent("我现在到哪一站了？")
    assert result["intent"] == "trip_assistant"
    assert result["needs_fallback"] is False


def test_intent_router_routes_trip_question_with_delete_negation_to_trip_assistant() -> None:
    result = score_intent("我们刚看完这里，下面怎么安排比较顺，不要删除任何景点。")
    assert result["intent"] == "trip_assistant"


def test_intent_router_delete_negation_meta_instruction_does_not_fallback_to_manual_edit() -> None:
    result = score_intent("我们刚看完这里，下面怎么安排比较顺，不要删除任何景点。不要把它误当成改路线或闲聊。")
    assert result["intent"] == "trip_assistant"
    assert result["needs_fallback"] is False


def test_intent_router_routes_weather_when_queue_lookup_is_negated() -> None:
    result = score_intent("别查排队人数，帮我看景山公园当前天气和温度。")
    assert result["intent"] == "weather_info"


def test_intent_router_routes_capability_question_with_task_examples_to_smalltalk() -> None:
    result = score_intent("如果我后面问故宫历史、导航和天气，你分别能怎么帮我？")
    assert result["intent"] == "smalltalk"
    assert result["needs_fallback"] is False


def test_intent_router_routes_first_use_capability_to_smalltalk_without_fallback() -> None:
    result = score_intent("我们现在有点赶时间，我第一次用这个导游，简单说说你会怎么回答问题。")
    assert result["intent"] == "smalltalk"
    assert result["needs_fallback"] is False


def test_intent_router_route_edit_meta_negation_keeps_greeting_smalltalk() -> None:
    result = score_intent("先打个招呼，等下我再问路线，现在不用操作行程。不要把它误当成改路线或闲聊。")
    assert result["intent"] == "smalltalk"
    assert result["needs_fallback"] is False


def test_intent_router_routes_thanks_with_negated_live_lookup_to_smalltalk() -> None:
    result = score_intent("谢谢你，刚才的建议我看到了，先不用继续查开放时间。")
    assert result["intent"] == "smalltalk"
    assert result["needs_fallback"] is False


def test_intent_router_routes_thanks_with_negated_live_and_meta_edit_to_smalltalk() -> None:
    result = score_intent("谢谢你，刚才的建议我看到了，先不用继续查开放时间。不要把它误当成改路线或闲聊。")
    assert result["intent"] == "smalltalk"
    assert result["needs_fallback"] is False


def test_intent_router_routes_tired_continue_question_to_trip_assistant() -> None:
    result = score_intent("老人有点累，但先不要改路线，接下来这个点还适合继续吗？")
    assert result["intent"] == "trip_assistant"


def test_intent_router_routes_direct_purchase_request_to_out_of_scope() -> None:
    result = score_intent("同行里有老人和孩子，帮我订两张今晚演出票，最好直接付款。")
    assert result["intent"] == "out_of_scope"


def test_intent_router_live_info_handles_zh_hard_colloquial_hours_query() -> None:
    result = score_intent("今天晚上景山大概几点关门？")
    assert result["intent"] == "live_info"


def test_intent_router_translation_handles_bilingual_display_variant() -> None:
    result = score_intent("帮我双语显示这段话")
    assert result["intent"] == "translation"


def test_intent_router_routes_transit_navigation_query_to_navigation_text() -> None:
    result = score_intent("从北京南站到故宫最快怎么坐地铁？")
    assert result["intent"] == "navigation_text"
    assert result["needs_fallback"] is False


def test_domain_guard_hard_deny_does_not_allow_rule_router_to_decide_final_intent() -> None:
    guard = evaluate_domain_support("现在买什么股票比较好？")
    router = score_intent("现在买什么股票比较好？")
    assert guard.hard_deny is True
    assert router["intent"] in {"live_info", "weather_info", "manual_route_edit_redirect", "out_of_scope"}
