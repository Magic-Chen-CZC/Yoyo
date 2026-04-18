from __future__ import annotations

from typing import Any

from yoyo.modules.knowledge.attraction_retriever import get_attraction_context


async def build_stop_summaries(
    stops: list[dict[str, Any]],
    *,
    session=None,
) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for stop in stops:
        stop_id = str(stop.get("id") or "")
        stop_name = stop.get("name")
        attraction = await get_attraction_context(stop_name if isinstance(stop_name, str) else None, session=session)
        if attraction is None:
            summaries[stop_id] = {
                "short_intro": None,
                "highlights": [],
                "visitor_tip": None,
                "source_type": None,
            }
            continue
        summaries[stop_id] = {
            "short_intro": attraction.short_intro,
            "highlights": list(attraction.highlights[:2]),
            "visitor_tip": attraction.visitor_tips[0] if attraction.visitor_tips else None,
            "source_type": attraction.source,
        }
    return summaries
