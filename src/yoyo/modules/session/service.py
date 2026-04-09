from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.itinerary import ItineraryVersion
from yoyo.db.models.session import GuideSession
from yoyo.modules.session.schemas import (
    CreateGuideSessionRequest,
    GPSUpdateRead,
    GuideSessionRead,
    SessionCurrentRead,
)
from yoyo.modules.shared.enums import GuidePlaybackState


async def create_guide_session(
    session: AsyncSession, payload: CreateGuideSessionRequest
) -> GuideSessionRead:
    guide_session = GuideSession(
        itinerary_id=payload.itinerary_id,
        itinerary_version_id=payload.itinerary_version_id,
        playback_state=GuidePlaybackState.NOT_TRIGGERED,
        context_json={
            "current_position": payload.context.get("current_position"),
            "current_stop_index": payload.context.get("current_stop_index", 0),
            "last_arrived_stop_id": payload.context.get("last_arrived_stop_id"),
            "last_played_stop_id": payload.context.get("last_played_stop_id"),
        },
    )
    session.add(guide_session)
    await session.commit()
    await session.refresh(guide_session)

    return _serialize_guide_session(guide_session)


async def get_guide_session(session: AsyncSession, guide_session_id: str) -> GuideSessionRead | None:
    guide_session = await session.get(GuideSession, guide_session_id)
    if guide_session is None:
        return None

    return _serialize_guide_session(guide_session)


async def get_guide_session_current(
    session: AsyncSession, guide_session_id: str
) -> SessionCurrentRead | None:
    guide_session = await session.get(GuideSession, guide_session_id)
    if guide_session is None:
        return None

    plan = await get_itinerary_version_plan(session, guide_session.itinerary_version_id)
    stops = plan.get("stops", []) if plan else []
    current_position = guide_session.context_json.get("current_position")
    current_stop_index = int(guide_session.context_json.get("current_stop_index", 0) or 0)
    current_stop = stops[current_stop_index] if len(stops) > current_stop_index else None
    next_stop = stops[current_stop_index + 1] if len(stops) > current_stop_index + 1 else None

    return SessionCurrentRead(
        guide_session_id=guide_session.id,
        itinerary_id=guide_session.itinerary_id,
        itinerary_version_id=guide_session.itinerary_version_id,
        status=guide_session.status.value,
        playback_state=guide_session.playback_state.value,
        current_stop=current_stop,
        next_stop=next_stop,
        current_position=current_position,
        stop_count=len(stops),
        plan_summary=plan.get("summary") if plan else None,
    )


async def update_gps_position(
    session: AsyncSession, guide_session_id: str, latitude: float, longitude: float
) -> GPSUpdateRead | None:
    guide_session = await session.get(GuideSession, guide_session_id)
    if guide_session is None:
        return None

    context = dict(guide_session.context_json)
    context["current_position"] = {"latitude": latitude, "longitude": longitude}

    plan = await get_itinerary_version_plan(session, guide_session.itinerary_version_id)
    stops = plan.get("stops", []) if plan else []
    current_stop_index = int(context.get("current_stop_index", 0) or 0)
    current_stop = stops[current_stop_index] if len(stops) > current_stop_index else None

    arrived = bool(current_stop)
    if arrived:
        context["last_arrived_stop_id"] = current_stop.get("id")
        if guide_session.playback_state == GuidePlaybackState.NOT_TRIGGERED:
            guide_session.playback_state = GuidePlaybackState.TRIGGERED

    guide_session.context_json = context
    await session.commit()
    await session.refresh(guide_session)

    return GPSUpdateRead(
        guide_session_id=guide_session.id,
        current_position={"latitude": latitude, "longitude": longitude},
        current_stop=current_stop,
        arrived=arrived,
    )


async def get_itinerary_version_plan(
    session: AsyncSession, itinerary_version_id: str
) -> dict | None:
    version = await session.get(ItineraryVersion, itinerary_version_id)
    if version is None:
        return None

    return version.plan_json


def _serialize_guide_session(guide_session: GuideSession) -> GuideSessionRead:
    return GuideSessionRead(
        id=guide_session.id,
        itinerary_id=guide_session.itinerary_id,
        itinerary_version_id=guide_session.itinerary_version_id,
        status=guide_session.status.value,
        context={
            **guide_session.context_json,
            "playback_state": guide_session.playback_state.value,
        },
    )
