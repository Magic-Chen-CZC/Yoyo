from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.session import GuideSession
from yoyo.modules.guide.playback import next_playback_state
from yoyo.modules.guide.schemas import GuideAssetRead, GuidePlaybackUpdateRead
from yoyo.modules.shared.enums import AssetStatus, GuideGenerationJobStatus


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

    guide_session.playback_state = next_playback_state(action)
    context = dict(guide_session.context_json)
    if action in {"play", "complete", "skip"}:
        context["last_playback_action"] = action
    if action == "play":
        context["last_played_stop_id"] = context.get("last_arrived_stop_id")
    guide_session.context_json = context
    await session.commit()
    await session.refresh(guide_session)

    return GuidePlaybackUpdateRead(
        guide_session_id=guide_session.id,
        playback_state=guide_session.playback_state.value,
    )
