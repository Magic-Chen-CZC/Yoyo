from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import ItineraryVersion
from yoyo.db.models.session import GuideSession
from yoyo.modules.guide.playback import next_playback_state
from yoyo.modules.guide.schemas import GuideAssetRead, GuidePlaybackUpdateRead
from yoyo.modules.session.runtime import (
    get_current_and_next_stop,
    get_current_stop_index,
    get_runtime_context,
    get_stops,
)
from yoyo.modules.shared.enums import AssetStatus, GuideGenerationJobStatus, GuidePlaybackState


async def get_active_guide_asset(
    session: AsyncSession, guide_session_id: str
) -> GuideAssetRead | None:
    guide_session = await session.get(GuideSession, guide_session_id)
    if guide_session is None:
        return None

    result = await session.execute(
        select(GuideGenerationJob)
        .where(GuideGenerationJob.itinerary_version_id == guide_session.itinerary_version_id)
        .where(GuideGenerationJob.status == GuideGenerationJobStatus.SUCCEEDED)
        .order_by(GuideGenerationJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()

    if job is None:
        return GuideAssetRead(
            guide_session_id=guide_session.id,
            playback_state=guide_session.playback_state.value,
            asset_status=AssetStatus.MISSING.value,
            summary=None,
            stops=[],
            result=None,
        )

    result_json = job.result_json or {}
    return GuideAssetRead(
        guide_session_id=guide_session.id,
        playback_state=guide_session.playback_state.value,
        asset_status=job.asset_status.value,
        summary=result_json.get("summary"),
        stops=result_json.get("stops", []),
        result=result_json,
    )


async def update_playback_state(
    session: AsyncSession, guide_session_id: str, action: str
) -> GuidePlaybackUpdateRead | None:
    guide_session = await session.get(GuideSession, guide_session_id)
    if guide_session is None:
        return None

    context = get_runtime_context(guide_session.context_json)
    version = await session.get(ItineraryVersion, guide_session.itinerary_version_id)
    stops = get_stops(version.plan_json if version else None)
    current_stop_index = get_current_stop_index(context, len(stops))
    current_stop, next_stop = get_current_and_next_stop(stops, current_stop_index)
    guide_session.playback_state = next_playback_state(action)

    if action in {"play", "complete", "skip"}:
        context["last_playback_action"] = action
    if action in {"complete", "skip"} and current_stop is not None:
        context["last_played_stop_id"] = current_stop.get("id")
        if context.get("last_arrived_stop_id") == current_stop.get("id") and next_stop is not None:
            context["current_stop_index"] = current_stop_index + 1
            context["last_arrived_stop_id"] = None
            guide_session.playback_state = GuidePlaybackState.NOT_TRIGGERED

    guide_session.context_json = context
    await session.commit()
    await session.refresh(guide_session)

    return GuidePlaybackUpdateRead(
        guide_session_id=guide_session.id,
        playback_state=guide_session.playback_state.value,
    )
