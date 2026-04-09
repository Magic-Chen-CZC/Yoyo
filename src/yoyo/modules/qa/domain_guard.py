SUPPORTED_KEYWORDS = {
    "beijing",
    "forbidden city",
    "tiananmen",
    "jingshan",
    "trip",
    "route",
    "itinerary",
    "attraction",
    "translate",
    "weather",
    "ticket",
    "guide",
}


def is_supported_query(query: str) -> bool:
    lowered = query.strip().lower()
    if not lowered:
        return False

    return any(keyword in lowered for keyword in SUPPORTED_KEYWORDS)
