from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.comments.service import summarize_comments_by_stop_ids
from yoyo.modules.knowledge.stop_summary_builder import build_stop_summaries
from yoyo.modules.map.service import build_map_payload
from yoyo.modules.session.service import get_guide_session_current, get_itinerary_version_plan

router = APIRouter(prefix="/map")


@router.get("/session/{guide_session_id}")
async def get_map_session(
    guide_session_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    current = await get_guide_session_current(session, guide_session_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guide session not found")

    plan = await get_itinerary_version_plan(session, current.itinerary_version_id)
    stops = plan.get("stops", []) if plan else []
    stop_summaries = await build_stop_summaries(stops, session=session)
    comment_summaries = await summarize_comments_by_stop_ids(
        session,
        [str(stop.get("id") or "") for stop in stops],
    )
    payload = build_map_payload(
        guide_session_id,
        stops,
        current.current_position,
        current.current_stop_index,
        stop_summaries=stop_summaries,
        comment_summaries=comment_summaries,
        route_polyline=list(plan.get("polyline") or []) if plan else [],
    )
    return success_response(payload.model_dump())
