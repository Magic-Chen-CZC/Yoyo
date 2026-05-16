# 这里维护“不同 intent 允许使用哪些技能”的映射表。
# 当前更像一份白名单配置，而不是复杂逻辑。
INTENT_SKILLS: dict[str, list[str]] = {
    "attraction_explain": ["get_current_poi", "get_attraction_info", "search_attraction_knowledge"],
    "trip_assistant": ["get_trip_context", "get_navigation_summary", "get_current_poi"],
    "live_info": ["search_live_info", "get_attraction_info"],
    "weather_info": ["get_weather_info", "get_current_poi"],
    "navigation_text": ["get_text_navigation", "get_trip_context", "get_current_poi"],
    "translation": ["translate_text"],
    "smalltalk": [],
    "manual_route_edit_redirect": [],
    "out_of_scope": [],
}


def get_allowed_skills(intent: str) -> list[str]:
    return INTENT_SKILLS.get(intent, [])
