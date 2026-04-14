from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.session import GuideSession
from yoyo.modules.guide.playback import next_playback_state
from yoyo.modules.guide.schemas import GuideAssetRead, GuidePlaybackUpdateRead
from yoyo.modules.shared.enums import AssetStatus, GuideGenerationJobStatus


# 这个文件负责两件事：
# 1) 读取当前 guide session 真正应该展示的导览素材
# 2) 更新播放状态（trigger / play / complete / skip）
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
        .where(GuideGenerationJob.asset_status == AssetStatus.READY)
        .order_by(
            func.coalesce(GuideGenerationJob.finished_at, GuideGenerationJob.created_at).desc(),
            GuideGenerationJob.created_at.desc(),
        )
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
    context["playback_state"] = guide_session.playback_state.value
    if action in {"trigger", "play", "complete", "skip"}:
        context["last_playback_action"] = action
        context["last_playback_updated_at"] = datetime.now(timezone.utc).isoformat()
    if action == "play":
        context["last_played_stop_id"] = context.get("last_arrived_stop_id")
        if isinstance(context.get("current_stop_index"), int):
            context["last_played_stop_index"] = context.get("current_stop_index")
    guide_session.context_json = context
    await session.commit()
    await session.refresh(guide_session)

    return GuidePlaybackUpdateRead(
        guide_session_id=guide_session.id,
        playback_state=guide_session.playback_state.value,
    )
