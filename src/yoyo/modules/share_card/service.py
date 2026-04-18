from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.itinerary import Itinerary
from yoyo.modules.comments.service import summarize_comments_by_stop_ids
from yoyo.modules.guide.asset_service import get_active_guide_asset
from yoyo.modules.knowledge.stop_summary_builder import build_stop_summaries
from yoyo.modules.session.service import get_guide_session, get_itinerary_version_plan
from yoyo.modules.share_card.schemas import MapPreviewRead, ShareCardRead, SocialSummaryRead, TripSummaryRead


async def build_share_card(
    session: AsyncSession,
    guide_session_id: str,
) -> ShareCardRead | None:
    guide_session = await get_guide_session(session, guide_session_id)
    if guide_session is None:
        return None

    itinerary = await session.get(Itinerary, guide_session.itinerary_id)
    plan = await get_itinerary_version_plan(session, guide_session.itinerary_version_id)
    stops = list((plan or {}).get("stops") or [])
    stop_ids = [str(stop.get("id") or "") for stop in stops]
    stop_names = [str(stop.get("name") or "") for stop in stops if stop.get("name")]
    stop_summaries = await build_stop_summaries(stops, session=session)
    comment_summaries = await summarize_comments_by_stop_ids(session, stop_ids)
    asset = await get_active_guide_asset(session, guide_session_id)

    is_shareable = guide_session.status == "finished"
    card_payload = ((asset.result or {}).get("card") if asset and asset.result else {}) or {}
    headline = str(card_payload.get("headline") or itinerary.title or (plan or {}).get("summary") or "Beijing trip recap")
    highlights = [str(item) for item in (card_payload.get("highlights") or []) if str(item).strip()]
    if not highlights:
        highlights = [name for name in stop_names[:3] if name]
    practical_tips = [str(item) for item in (card_payload.get("practical_tips") or []) if str(item).strip()]
    route_style = card_payload.get("route_style")
    guide_style = card_payload.get("guide_style")

    comment_count_total = sum(int((comment_summaries.get(stop_id) or {}).get("comment_count") or 0) for stop_id in stop_ids)
    top_stop_id = max(
        stop_ids,
        key=lambda stop_id: int((comment_summaries.get(stop_id) or {}).get("comment_count") or 0),
        default=None,
    )
    top_commented_stop_name = None
    featured_comment_preview = None
    if top_stop_id is not None:
        for stop in stops:
            if str(stop.get("id") or "") == top_stop_id:
                top_commented_stop_name = str(stop.get("name") or "") or None
                break
        featured_comment_preview = (comment_summaries.get(top_stop_id) or {}).get("latest_comment_preview")

    if featured_comment_preview is None:
        for stop_id in stop_ids:
            preview = (comment_summaries.get(stop_id) or {}).get("latest_comment_preview")
            if preview:
                featured_comment_preview = str(preview)
                break

    markers_preview = []
    for index, stop in enumerate(stops[:3]):
        stop_id = str(stop.get("id") or "")
        summary = dict(stop_summaries.get(stop_id) or {})
        comment_summary = dict(comment_summaries.get(stop_id) or {})
        markers_preview.append(
            {
                "id": stop.get("id"),
                "name": stop.get("name"),
                "order": index,
                "short_intro": summary.get("short_intro"),
                "comment_count": int(comment_summary.get("comment_count") or 0),
            }
        )

    subheadline = None
    if guide_session.context.get("trip_finished_at"):
        subheadline = "Trip complete — ready to share"

    return ShareCardRead(
        guide_session_id=guide_session.id,
        status=guide_session.status,
        is_shareable=is_shareable,
        headline=headline,
        subheadline=subheadline,
        highlights=highlights,
        route_style=str(route_style) if route_style else None,
        guide_style=str(guide_style) if guide_style else None,
        practical_tips=practical_tips,
        trip_summary=TripSummaryRead(
            itinerary_title=itinerary.title if itinerary else None,
            stop_count=len(stops),
            stops_preview=stop_names[:3],
            completed_at=guide_session.context.get("trip_finished_at"),
        ),
        social_summary=SocialSummaryRead(
            comment_count_total=comment_count_total,
            featured_comment_preview=str(featured_comment_preview) if featured_comment_preview else None,
            top_commented_stop_name=top_commented_stop_name,
        ),
        map_preview=MapPreviewRead(
            polyline=list((plan or {}).get("polyline") or []),
            markers_preview=markers_preview,
        ),
    )
