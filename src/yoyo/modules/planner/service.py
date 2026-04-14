from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import Itinerary, ItineraryVersion
from yoyo.db.models.session import GuideSession
from yoyo.jobs.queue import get_job_pool
from yoyo.modules.planner.rules import build_default_plan
from yoyo.modules.planner.schemas import (
    CreateItineraryRequest,
    ItineraryRead,
    ItineraryVersionRead,
    RouteEditRequest,
)
from yoyo.modules.planner.stop_catalog import get_canonical_stop
from yoyo.modules.session.runtime import get_current_stop_index, remap_current_stop_index
from yoyo.modules.shared.enums import (
    AssetStatus,
    GuideGenerationJobStatus,
    GuideGenerationJobType,
    GuidePlaybackState,
    GuideSessionStatus,
    ItineraryStatus,
    ItineraryVersionStatus,
)


async def create_itinerary(session: AsyncSession, payload: CreateItineraryRequest) -> ItineraryRead:
    planner_input = {
        "questionnaire_submission_id": payload.questionnaire_submission_id,
        "user_id": payload.user_id,
        "preferences": payload.preferences,
    }
    plan = build_default_plan(payload.preferences)

    itinerary = Itinerary(
        user_id=payload.user_id,
        city_code=payload.city_code,
        title=payload.title,
        status=ItineraryStatus.ACTIVE,
    )
    session.add(itinerary)
    await session.flush()

    version = ItineraryVersion(
        itinerary_id=itinerary.id,
        version_no=1,
        planner_input_json=planner_input,
        plan_json=plan,
        status=ItineraryVersionStatus.ACTIVE,
        created_by="planner_v0",
    )
    session.add(version)
    await session.flush()

    itinerary.current_version_id = version.id

    job = GuideGenerationJob(
        itinerary_version_id=version.id,
        job_type=GuideGenerationJobType.GUIDE_BUNDLE,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        payload_json={"itinerary_id": itinerary.id, "itinerary_version_id": version.id},
    )
    session.add(job)
    await session.commit()
    await session.refresh(itinerary)
    await session.refresh(version)
    await session.refresh(job)

    redis = await get_job_pool()
    await redis.enqueue_job("run_guide_generation_job", job.id)

    return _serialize_itinerary(itinerary, version)


async def get_itinerary(session: AsyncSession, itinerary_id: str) -> ItineraryRead | None:
    itinerary, version = await _get_itinerary_and_current_version(session, itinerary_id)
    if itinerary is None or version is None:
        return None

    return _serialize_itinerary(itinerary, version)


async def list_itinerary_versions(
    session: AsyncSession, itinerary_id: str
) -> list[ItineraryVersionRead] | None:
    itinerary = await session.get(Itinerary, itinerary_id)
    if itinerary is None:
        return None

    result = await session.execute(
        select(ItineraryVersion)
        .where(ItineraryVersion.itinerary_id == itinerary_id)
        .order_by(ItineraryVersion.version_no.desc())
    )
    versions = result.scalars().all()
    return [_serialize_itinerary_version(version) for version in versions]


async def edit_itinerary(
    session: AsyncSession, itinerary_id: str, payload: RouteEditRequest
) -> ItineraryRead | None:
    itinerary, current_version = await _get_itinerary_and_current_version(session, itinerary_id)
    if itinerary is None or current_version is None:
        return None

    current_plan = deepcopy(current_version.plan_json)
    current_stops = [dict(stop) for stop in current_plan.get("stops", [])]
    edited_plan = _build_edited_plan(current_plan, payload)
    edited_stops = [dict(stop) for stop in edited_plan.get("stops", [])]

    current_version.status = ItineraryVersionStatus.ARCHIVED
    new_version = ItineraryVersion(
        itinerary_id=itinerary.id,
        version_no=current_version.version_no + 1,
        planner_input_json=deepcopy(current_version.planner_input_json),
        plan_json=edited_plan,
        status=ItineraryVersionStatus.ACTIVE,
        created_by=payload.created_by,
    )
    session.add(new_version)
    await session.flush()

    itinerary.current_version_id = new_version.id
    await _switch_active_sessions_to_new_version(
        session=session,
        itinerary_id=itinerary.id,
        new_version_id=new_version.id,
        old_stops=current_stops,
        new_stops=edited_stops,
    )

    job = GuideGenerationJob(
        itinerary_version_id=new_version.id,
        job_type=GuideGenerationJobType.GUIDE_BUNDLE,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        payload_json={"itinerary_id": itinerary.id, "itinerary_version_id": new_version.id},
    )
    session.add(job)
    await session.commit()
    await session.refresh(itinerary)
    await session.refresh(new_version)
    await session.refresh(job)

    redis = await get_job_pool()
    await redis.enqueue_job("run_guide_generation_job", job.id)

    return _serialize_itinerary(itinerary, new_version)


def _serialize_itinerary(itinerary: Itinerary, version: ItineraryVersion) -> ItineraryRead:
    return ItineraryRead(
        id=itinerary.id,
        user_id=itinerary.user_id,
        city_code=itinerary.city_code,
        title=itinerary.title,
        status=itinerary.status.value,
        current_version_id=itinerary.current_version_id,
        version=_serialize_itinerary_version(version),
    )


def _serialize_itinerary_version(version: ItineraryVersion) -> ItineraryVersionRead:
    return ItineraryVersionRead(
        id=version.id,
        version_no=version.version_no,
        status=version.status.value,
        planner_input=version.planner_input_json,
        plan=version.plan_json,
    )


async def _get_itinerary_and_current_version(
    session: AsyncSession, itinerary_id: str
) -> tuple[Itinerary | None, ItineraryVersion | None]:
    itinerary = await session.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.current_version_id is None:
        return itinerary, None

    version = await session.get(ItineraryVersion, itinerary.current_version_id)
    return itinerary, version


def _build_edited_plan(plan: dict, payload: RouteEditRequest) -> dict:
    edited_plan = deepcopy(plan)
    edited_stops = [dict(stop) for stop in edited_plan.get("stops", [])]

    if payload.operation == "replace_stop":
        target_index = _find_target_stop_index(
            edited_stops,
            target_stop_id=payload.target_stop_id,
            target_stop_name=payload.target_stop_name,
        )
        replacement_stop = get_canonical_stop(
            stop_id=payload.replacement_stop_id,
            stop_name=payload.replacement_stop_name,
        )
        if replacement_stop is None:
            raise ValueError("replacement stop not found")

        target_stop_id = edited_stops[target_index].get("id")
        replacement_stop_id = replacement_stop.get("id")
        if replacement_stop_id == target_stop_id:
            raise ValueError("replacement stop must differ from target stop")
        if any(
            stop.get("id") == replacement_stop_id and index != target_index
            for index, stop in enumerate(edited_stops)
        ):
            raise ValueError("replacement stop already exists in route")
        edited_stops[target_index] = replacement_stop

    elif payload.operation == "remove_stop":
        target_index = _find_target_stop_index(
            edited_stops,
            target_stop_id=payload.target_stop_id,
            target_stop_name=payload.target_stop_name,
        )
        if len(edited_stops) <= 1:
            raise ValueError("route must contain at least one stop")
        edited_stops.pop(target_index)

    elif payload.operation == "reorder_stops":
        current_stop_ids = [str(stop.get("id")) for stop in edited_stops]
        ordered_stop_ids = [str(stop_id) for stop_id in payload.ordered_stop_ids]
        if len(set(ordered_stop_ids)) != len(current_stop_ids):
            raise ValueError("ordered_stop_ids must not contain duplicates")
        if set(ordered_stop_ids) != set(current_stop_ids):
            raise ValueError("ordered_stop_ids must match current route stops")
        stop_by_id = {str(stop.get("id")): stop for stop in edited_stops}
        edited_stops = [stop_by_id[stop_id] for stop_id in ordered_stop_ids]

    elif payload.operation == "shorten_route":
        target_stop_count = int(payload.target_stop_count or 0)
        if target_stop_count < 1 or target_stop_count > len(edited_stops):
            raise ValueError("target_stop_count must be between 1 and current stop count")
        edited_stops = edited_stops[:target_stop_count]

    edited_plan["stops"] = edited_stops
    return edited_plan


def _find_target_stop_index(
    stops: list[dict],
    *,
    target_stop_id: str | None,
    target_stop_name: str | None,
) -> int:
    if target_stop_id is not None:
        for index, stop in enumerate(stops):
            if stop.get("id") == target_stop_id:
                return index

    if target_stop_name is not None:
        lowered_name = target_stop_name.strip().lower()
        for index, stop in enumerate(stops):
            if str(stop.get("name", "")).lower() == lowered_name:
                return index

    raise ValueError("target stop not found in route")


async def _switch_active_sessions_to_new_version(
    session: AsyncSession,
    itinerary_id: str,
    new_version_id: str,
    old_stops: list[dict],
    new_stops: list[dict],
) -> None:
    result = await session.execute(
        select(GuideSession)
        .where(GuideSession.itinerary_id == itinerary_id)
        .where(GuideSession.status == GuideSessionStatus.ACTIVE)
    )
    active_sessions = result.scalars().all()
    valid_stop_ids = {stop.get("id") for stop in new_stops}

    for guide_session in active_sessions:
        context = dict(guide_session.context_json or {})
        current_stop_index = get_current_stop_index(context, len(old_stops))
        remapped_index, current_stop_changed = remap_current_stop_index(
            old_stops,
            new_stops,
            current_stop_index,
        )
        context["current_stop_index"] = remapped_index

        last_arrived_stop_id = context.get("last_arrived_stop_id")
        if current_stop_changed or last_arrived_stop_id not in valid_stop_ids:
            context["last_arrived_stop_id"] = None

        if context.get("last_played_stop_id") not in valid_stop_ids:
            context["last_played_stop_id"] = None

        if current_stop_changed:
            guide_session.playback_state = GuidePlaybackState.NOT_TRIGGERED
            context.pop("last_playback_action", None)

        guide_session.itinerary_version_id = new_version_id
        guide_session.context_json = context
