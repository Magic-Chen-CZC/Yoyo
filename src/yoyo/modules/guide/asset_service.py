from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import ItineraryVersion
from yoyo.db.models.session import GuideSession
from yoyo.modules.guide.playback import next_playback_state
from yoyo.modules.guide.schemas import GuideAssetRead, GuideAudioSegmentRead, GuidePlaybackUpdateRead, GuideSegmentCycleRead
from yoyo.modules.guide.tts import synthesize_text_segment
from yoyo.modules.knowledge.attraction_retriever import get_attraction_context
from yoyo.modules.knowledge.profile_retriever import get_profile_context
from yoyo.modules.session.runtime import (
    get_current_and_next_stop,
    get_current_stop_index,
    get_runtime_context,
    get_stops,
)
from yoyo.modules.shared.enums import AssetStatus, GuideGenerationJobStatus, GuidePlaybackState, GuideSessionStatus


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

    context = get_runtime_context(guide_session.context_json)
    version = await session.get(ItineraryVersion, guide_session.itinerary_version_id)
    stops = get_stops(version.plan_json if version else None)
    current_stop_index = get_current_stop_index(context, len(stops))
    current_stop, next_stop = get_current_and_next_stop(stops, current_stop_index)
    guide_session.playback_state = next_playback_state(action)

    context["playback_state"] = guide_session.playback_state.value
    if action in {"trigger", "play", "complete", "skip"}:
        context["last_playback_action"] = action
        context["last_playback_updated_at"] = datetime.now(timezone.utc).isoformat()
    if action == "play":
        context["last_played_stop_id"] = context.get("last_arrived_stop_id") or (
            current_stop.get("id") if current_stop is not None else None
        )
        context["last_played_stop_index"] = current_stop_index
    if action in {"complete", "skip"} and current_stop is not None:
        context["last_played_stop_id"] = current_stop.get("id")
        context["last_played_stop_index"] = current_stop_index
        if context.get("last_arrived_stop_id") == current_stop.get("id"):
            if next_stop is not None:
                context["current_stop_index"] = current_stop_index + 1
                context["last_arrived_stop_id"] = None
                guide_session.playback_state = GuidePlaybackState.NOT_TRIGGERED
                context["playback_state"] = guide_session.playback_state.value
            else:
                context["current_stop_index"] = len(stops)
                context["last_arrived_stop_id"] = None
                context["playback_state"] = guide_session.playback_state.value

    guide_session.context_json = context
    await session.commit()
    await session.refresh(guide_session)

    return GuidePlaybackUpdateRead(
        guide_session_id=guide_session.id,
        playback_state=guide_session.playback_state.value,
    )


async def cycle_guide_segments(
    session: AsyncSession,
    guide_session_id: str,
    action: str,
) -> GuideSegmentCycleRead | None:
    guide_session = await session.get(GuideSession, guide_session_id)
    if guide_session is None or guide_session.status == GuideSessionStatus.FINISHED:
        return None

    context = get_runtime_context(guide_session.context_json)
    version = await session.get(ItineraryVersion, guide_session.itinerary_version_id)
    stops = get_stops(version.plan_json if version else None)
    current_stop_index = get_current_stop_index(context, len(stops))
    current_stop, _ = get_current_and_next_stop(stops, current_stop_index)
    if current_stop is None:
        return None

    active_asset = await get_active_guide_asset(session, guide_session_id)
    if active_asset is None or active_asset.result is None:
        return None

    stop_payload = _find_stop_payload(active_asset.result, current_stop.get("id"), current_stop.get("name"))
    if stop_payload is None:
        return None

    stop_id = str(stop_payload.get("stop_id") or current_stop.get("id") or "")
    attraction = await get_attraction_context(
        str(stop_payload.get("stop_name") or current_stop.get("name") or "") or None,
        session=session,
    )
    segments = [str(item) for item in list((attraction.guide_segments if attraction else []) or []) if str(item).strip()]
    if not segments:
        segments = [str(item) for item in list(stop_payload.get("guide_segments") or []) if str(item).strip()]
    if not segments:
        narration = str(stop_payload.get("narration") or "").strip()
        segments = [narration] if narration else []
    segment_count = int(attraction and len(attraction.guide_segments) or stop_payload.get("segment_count") or len(segments))
    guide_style = ((active_asset.result or {}).get("card") or {}).get("guide_style")

    cursor_map = dict(context.get("stop_segment_cursor_by_stop_id") or {})
    played_map = dict(context.get("played_segment_indices_by_stop_id") or {})
    cursor = int(cursor_map.get(stop_id) or 0)
    played_indices = [int(item) for item in list(played_map.get(stop_id) or [])]
    batch_size = 2

    if action != "cycle_content":
        return None

    start = min(cursor, len(segments))
    selected_indices = list(range(start, min(start + batch_size, len(segments))))
    if not selected_indices:
        available_indices = [index for index in range(len(segments)) if index not in played_indices]
        if not available_indices:
            available_indices = list(range(len(segments)))
        selected_indices = available_indices[:batch_size]
    cursor_map[stop_id] = start + len(selected_indices)

    for index in selected_indices:
        if index not in played_indices:
            played_indices.append(index)
    played_map[stop_id] = played_indices
    context["stop_segment_cursor_by_stop_id"] = cursor_map
    context["played_segment_indices_by_stop_id"] = played_map
    context["last_refresh_action"] = action
    context["last_refresh_at"] = datetime.now(timezone.utc).isoformat()
    guide_session.context_json = context
    await session.commit()
    await session.refresh(guide_session)

    selected_segments = [segments[index] for index in selected_indices]
    stop_name = str(stop_payload.get("stop_name") or current_stop.get("name") or "") or None
    profile = await get_profile_context(str((active_asset.result or {}).get("generation_metadata", {}).get("profile_user_id") or "") or None, session=session)
    audio_segments = []
    for local_index, segment in zip(selected_indices, selected_segments, strict=False):
        audio_segments.append(
            GuideAudioSegmentRead.model_validate(
                await synthesize_text_segment(
                    stop_id=stop_id,
                    stop_name=stop_name,
                    segment_index=local_index,
                    text=segment,
                    profile=profile,
                )
            )
        )
    return GuideSegmentCycleRead(
        guide_session_id=guide_session.id,
        stop_id=stop_id or None,
        stop_name=stop_name,
        action=action,
        segments=selected_segments,
        audio_segments=audio_segments,
        segment_count=segment_count,
        more_content_available=len(set(played_indices)) < segment_count,
        guide_style=str(guide_style) if guide_style else None,
    )



def _find_stop_payload(result: dict[str, object], stop_id: object, stop_name: object) -> dict[str, object] | None:
    guide_script = result.get("guide_script") if isinstance(result, dict) else None
    stops = guide_script.get("stops") if isinstance(guide_script, dict) else None
    if not isinstance(stops, list):
        return None
    for item in stops:
        if not isinstance(item, dict):
            continue
        if stop_id is not None and item.get("stop_id") == stop_id:
            return item
        if stop_name is not None and item.get("stop_name") == stop_name:
            return item
    return None
