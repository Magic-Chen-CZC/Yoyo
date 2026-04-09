def detect_intent(query: str) -> str:
    lowered = query.lower()

    if any(keyword in lowered for keyword in ["translate", "translation", "rewrite"]):
        return "translation"
    if any(keyword in lowered for keyword in ["weather", "open", "hours", "ticket", "today"]):
        return "live_info"
    if any(
        keyword in lowered
        for keyword in [
            "replace",
            "swap",
            "remove",
            "change route",
            "reorder",
            "shorten",
            "fewer",
        ]
    ):
        return "planner_handoff"
    if any(keyword in lowered for keyword in ["next stop", "next", "route", "itinerary", "where should", "how long"]):
        return "trip_assistant"

    return "attraction_explain"
