from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.itinerary import ItineraryVersion
from yoyo.db.models.session import GuideSession
from yoyo.modules.session.runtime import (
    distance_to_stop_meters,
    get_arrival_threshold_meters,
    get_current_and_next_stop,
    get_current_stop_index,
    get_runtime_context,
    get_stops,
)
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
    context = get_runtime_context(payload.context)
    guide_session = GuideSession(
        itinerary_id=payload.itinerary_id,
        itinerary_version_id=payload.itinerary_version_id,
        playback_state=GuidePlaybackState.NOT_TRIGGERED,
        context_json=context,
    )
    session.add(guide_session)
    await session.commit()
    await session.refresh(guide_session)

    return _serialize_guide_session(guide_session)


async def get_guide_session(
    session: AsyncSession, guide_session_id: str
) -> GuideSessionRead | None:
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
    stops = get_stops(plan)
    context = get_runtime_context(guide_session.context_json)
    current_position = context.get("current_position")
    current_stop_index = get_current_stop_index(context, len(stops))
    current_stop, next_stop = get_current_and_next_stop(stops, current_stop_index)

    return SessionCurrentRead(
        guide_session_id=guide_session.id,
        itinerary_id=guide_session.itinerary_id,
        itinerary_version_id=guide_session.itinerary_version_id,
        status=guide_session.status.value,
        playback_state=guide_session.playback_state.value,
        current_stop_index=current_stop_index,
        has_next_stop=next_stop is not None,
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

    context = get_runtime_context(guide_session.context_json)
    context["current_position"] = {"latitude": latitude, "longitude": longitude}

    plan = await get_itinerary_version_plan(session, guide_session.itinerary_version_id)
    stops = get_stops(plan)
    current_stop_index = get_current_stop_index(context, len(stops))
    current_stop, _ = get_current_and_next_stop(stops, current_stop_index)
    distance_to_current_stop = distance_to_stop_meters(context["current_position"], current_stop)
    arrival_threshold = get_arrival_threshold_meters(current_stop)
    arrived = (
        current_stop is not None
        and distance_to_current_stop is not None
        and arrival_threshold is not None
        and distance_to_current_stop <= arrival_threshold
    )
    if arrived and context.get("last_arrived_stop_id") != current_stop.get("id"):
        context["last_arrived_stop_id"] = current_stop.get("id")
        if guide_session.playback_state == GuidePlaybackState.NOT_TRIGGERED:
            guide_session.playback_state = GuidePlaybackState.TRIGGERED

    guide_session.context_json = context
    await session.commit()
    await session.refresh(guide_session)

    return GPSUpdateRead(
        guide_session_id=guide_session.id,
        current_position={"latitude": latitude, "longitude": longitude},
        current_stop_index=current_stop_index,
        current_stop=current_stop,
        distance_to_current_stop_meters=distance_to_current_stop,
        arrival_threshold_meters=arrival_threshold,
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
    context = get_runtime_context(guide_session.context_json)
    return GuideSessionRead(
        id=guide_session.id,
        itinerary_id=guide_session.itinerary_id,
        itinerary_version_id=guide_session.itinerary_version_id,
        status=guide_session.status.value,
        context={
            **context,
            "playback_state": guide_session.playback_state.value,
        },
    )
