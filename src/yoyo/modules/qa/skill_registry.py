INTENT_SKILLS: dict[str, list[str]] = {
    "attraction_explain": ["get_current_poi", "get_attraction_info", "search_attraction_knowledge"],
    "trip_assistant": ["get_trip_context", "get_navigation_summary", "get_current_poi"],
    "live_info": ["search_live_info", "get_attraction_info"],
    "translation": ["translate_text"],
    "planner_handoff": ["handoff_to_planner"],
}


def get_allowed_skills(intent: str) -> list[str]:
    return INTENT_SKILLS.get(intent, [])
