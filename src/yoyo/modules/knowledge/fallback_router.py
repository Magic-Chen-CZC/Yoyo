from __future__ import annotations

from yoyo.modules.knowledge.schemas import AttractionContext


DETAILED_ATTRACTION_EXPLAIN_TOKENS = {
    "history",
    "story",
    "background",
    "meaning",
    "important",
    "deeper",
    "detail",
    "details",
    "why",
    "更多",
    "详细",
    "背景",
    "意义",
}


def should_use_rag_fallback(
    *,
    intent: str,
    query: str,
    attraction: AttractionContext | None,
) -> bool:
    if intent != "attraction_explain":
        return False
    if attraction is None:
        return False
    lowered = query.lower()
    if any(token in lowered for token in DETAILED_ATTRACTION_EXPLAIN_TOKENS):
        return True
    return len(attraction.history.split()) < 12
