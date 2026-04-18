from __future__ import annotations

from yoyo.modules.knowledge.schemas import LiveInfoContext
from yoyo.modules.qa.live_info import build_live_info_payload


async def get_live_info_context(query: str, attraction_name: str | None) -> LiveInfoContext:
    payload = await build_live_info_payload(query, attraction_name)
    return LiveInfoContext(
        summary=str(payload.get("summary") or ""),
        sources=list(payload.get("sources") or []),
        updated_at=payload.get("updated_at"),
        confidence=str(payload.get("confidence") or "low"),
        not_confirmed=bool(payload.get("not_confirmed")),
        source="live_search",
        status=str(payload.get("status") or "available"),
        reason=payload.get("reason"),
    )
