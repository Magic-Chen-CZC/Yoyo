# domain guard 是 QA 的第一道门。
# 当前实现仍是规则优先，但覆盖更多旅游/导览表达。
SUPPORTED_KEYWORDS = {
    "beijing",
    "forbidden city",
    "tiananmen",
    "jingshan",
    "temple of heaven",
    "summer palace",
    "trip",
    "route",
    "itinerary",
    "attraction",
    "translate",
    "translation",
    "weather",
    "ticket",
    "guide",
    "museum",
    "park",
    "palace",
    "next stop",
    "opening hours",
    "景点",
    "路线",
    "导览",
    "翻译",
    "下一站",
}


def is_supported_query(query: str) -> bool:
    lowered = query.strip().lower()
    if not lowered:
        return False

    return any(keyword in lowered for keyword in SUPPORTED_KEYWORDS)
