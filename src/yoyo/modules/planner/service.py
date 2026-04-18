from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import Itinerary, ItineraryVersion
from yoyo.db.models.session import GuideSession
from yoyo.jobs.queue import get_job_pool
from yoyo.modules.planner.optimization_service import apply_route_optimization
from yoyo.modules.planner.plan_builder import build_plan_from_entry
from yoyo.modules.planner.route_engine import apply_route_engine
from yoyo.modules.planner.schemas import (
    CreateItineraryRequest,
    ItineraryRead,
    ItineraryVersionRead,
    RouteEditRequest,
)
from yoyo.modules.planner.stop_catalog import get_canonical_stop
from yoyo.modules.session.runtime import (
    get_current_stop_index,
    remap_current_stop_index,
)
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
    plan, planner_entry = build_plan_from_entry(
        entry_type=payload.entry_type,
        preferences=payload.preferences,
        template_id=payload.template_id,
        selected_poi_ids=payload.selected_poi_ids,
    )
    plan = apply_route_optimization(
        plan,
        source=str((plan.get("route_meta") or {}).get("waypoint_order_source") or payload.entry_type),
        reorder_stops=False,
    )
    plan = await apply_route_engine(
        plan,
        reorder_stops=payload.entry_type in {"manual_poi", "ai_recommendation_selected"},
    )
    planner_input = {
        "questionnaire_submission_id": payload.questionnaire_submission_id,
        "user_id": payload.user_id,
        "preferences": payload.preferences,
        "entry_type": payload.entry_type,
        **planner_entry,
    }

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
    editable_from_stop_index = await _resolve_editable_from_stop_index(
        session,
        itinerary_id=itinerary.id,
        stop_count=len(current_stops),
    )
    if itinerary.status == ItineraryStatus.COMPLETED or (
        current_stops and editable_from_stop_index >= len(current_stops)
    ):
        raise ValueError("completed itinerary cannot be edited")
    edited_plan = _build_edited_plan(current_plan, payload, editable_from_stop_index)
    edited_plan = await _apply_route_engine_with_editable_boundary(
        edited_plan,
        editable_from_stop_index=editable_from_stop_index,
        reorder_stops=payload.operation in {"add_stop", "optimize_route"},
    )
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


def _build_edited_plan(plan: dict, payload: RouteEditRequest, editable_from_stop_index: int) -> dict:
    edited_plan = deepcopy(plan)
    edited_stops = [dict(stop) for stop in edited_plan.get("stops", [])]

    if payload.operation == "replace_stop":
        target_index = _find_target_stop_index(
            edited_stops,
            target_stop_id=payload.target_stop_id,
            target_stop_name=payload.target_stop_name,
        )
        _ensure_stop_index_is_editable(target_index, editable_from_stop_index)
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
        _ensure_stop_index_is_editable(target_index, editable_from_stop_index)
        if len(edited_stops) <= 1:
            raise ValueError("route must contain at least one stop")
        if len(edited_stops) - 1 < editable_from_stop_index + 1:
            raise ValueError("route must keep the current stop and completed route prefix")
        edited_stops.pop(target_index)

    elif payload.operation == "add_stop":
        add_stop = get_canonical_stop(
            stop_id=payload.add_stop_id,
            stop_name=payload.add_stop_name,
        )
        if add_stop is None:
            raise ValueError("add stop not found")
        add_stop_id = add_stop.get("id")
        if any(stop.get("id") == add_stop_id for stop in edited_stops):
            raise ValueError("add stop already exists in route")
        editable_suffix = edited_stops[editable_from_stop_index:]
        editable_suffix.append(add_stop)
        edited_stops = edited_stops[:editable_from_stop_index] + editable_suffix

    elif payload.operation == "reorder_stops":
        current_stop_ids = [str(stop.get("id")) for stop in edited_stops]
        ordered_stop_ids = [str(stop_id) for stop_id in payload.ordered_stop_ids]
        if len(set(ordered_stop_ids)) != len(current_stop_ids):
            raise ValueError("ordered_stop_ids must not contain duplicates")
        if set(ordered_stop_ids) != set(current_stop_ids):
            raise ValueError("ordered_stop_ids must match current route stops")
        if ordered_stop_ids[:editable_from_stop_index] != current_stop_ids[:editable_from_stop_index]:
            raise ValueError("ordered_stop_ids must preserve the completed route prefix")
        stop_by_id = {str(stop.get("id")): stop for stop in edited_stops}
        edited_stops = [stop_by_id[stop_id] for stop_id in ordered_stop_ids]

    elif payload.operation == "shorten_route":
        target_stop_count = int(payload.target_stop_count or 0)
        if target_stop_count < 1 or target_stop_count > len(edited_stops):
            raise ValueError("target_stop_count must be between 1 and current stop count")
        if target_stop_count < editable_from_stop_index + 1:
            raise ValueError("target_stop_count must keep the current stop and completed route prefix")
        edited_stops = edited_stops[:target_stop_count]

    edited_plan["stops"] = edited_stops
    optimization_source = "manual_reorder" if payload.operation == "reorder_stops" else "route_edit"
    if payload.operation == "optimize_route":
        optimization_source = "optimize_route"
    if payload.operation == "reorder_stops":
        edited_plan["route_meta"] = {
            **dict(edited_plan.get("route_meta") or {}),
            "optimization_status": "optimized",
            "routing_provider": None,
            "waypoint_order_source": optimization_source,
        }
        return edited_plan
    edited_plan = _apply_route_optimization_with_editable_boundary(
        edited_plan,
        editable_from_stop_index=editable_from_stop_index,
        source=optimization_source,
        reorder_stops=payload.operation in {"add_stop", "optimize_route"},
    )
    return edited_plan


async def _resolve_editable_from_stop_index(
    session: AsyncSession,
    *,
    itinerary_id: str,
    stop_count: int,
) -> int:
    result = await session.execute(
        select(GuideSession)
        .where(GuideSession.itinerary_id == itinerary_id)
        .where(GuideSession.status.in_([GuideSessionStatus.PENDING, GuideSessionStatus.ACTIVE]))
    )
    active_sessions = result.scalars().all()
    if not active_sessions or stop_count <= 0:
        return 0

    return max(
        get_current_stop_index(dict(guide_session.context_json or {}), stop_count)
        for guide_session in active_sessions
    )



def _apply_route_optimization_with_editable_boundary(
    plan: dict,
    *,
    editable_from_stop_index: int,
    source: str,
    reorder_stops: bool,
) -> dict:
    scoped_plan = dict(plan)
    stops = [dict(stop) for stop in scoped_plan.get("stops", [])]
    if not reorder_stops or editable_from_stop_index <= 0 or editable_from_stop_index >= len(stops):
        return apply_route_optimization(scoped_plan, source=source, reorder_stops=reorder_stops)

    frozen_prefix = stops[:editable_from_stop_index]
    editable_suffix = stops[editable_from_stop_index:]
    optimized_suffix_plan = apply_route_optimization(
        {**scoped_plan, "stops": editable_suffix},
        source=source,
        reorder_stops=True,
    )
    scoped_plan["stops"] = frozen_prefix + [dict(stop) for stop in optimized_suffix_plan.get("stops", [])]
    scoped_plan["route_meta"] = dict(optimized_suffix_plan.get("route_meta") or {})
    return scoped_plan



async def _apply_route_engine_with_editable_boundary(
    plan: dict,
    *,
    editable_from_stop_index: int,
    reorder_stops: bool,
) -> dict:
    scoped_plan = dict(plan)
    stops = [dict(stop) for stop in scoped_plan.get("stops", [])]
    if not reorder_stops or editable_from_stop_index <= 0 or editable_from_stop_index >= len(stops):
        return await apply_route_engine(scoped_plan, reorder_stops=reorder_stops)

    frozen_prefix = stops[:editable_from_stop_index]
    editable_suffix = stops[editable_from_stop_index:]
    suffix_plan = {
        **scoped_plan,
        "stops": editable_suffix,
    }
    routed_suffix_plan = await apply_route_engine(suffix_plan, reorder_stops=True)
    routed_suffix_stops = [dict(stop) for stop in routed_suffix_plan.get("stops", editable_suffix)]
    scoped_plan["stops"] = frozen_prefix + routed_suffix_stops
    scoped_plan["route_meta"] = dict(routed_suffix_plan.get("route_meta") or {})
    scoped_plan["polyline"] = _build_polyline_for_prefixed_route(
        frozen_prefix,
        routed_suffix_stops,
        routed_suffix_plan.get("polyline") or [],
    )
    return scoped_plan



def _build_polyline_for_prefixed_route(
    frozen_prefix: list[dict],
    routed_suffix_stops: list[dict],
    routed_suffix_polyline: list[dict],
) -> list[dict]:
    polyline: list[dict] = []
    order = 0
    for stop in frozen_prefix:
        polyline.append(
            {
                "stop_id": stop.get("id"),
                "order": order,
                "latitude": float(stop.get("latitude") or 0),
                "longitude": float(stop.get("longitude") or 0),
            }
        )
        order += 1
    if routed_suffix_polyline:
        for item in routed_suffix_polyline:
            polyline.append(
                {
                    "stop_id": item.get("stop_id"),
                    "order": order,
                    "latitude": float(item.get("latitude") or 0),
                    "longitude": float(item.get("longitude") or 0),
                }
            )
            order += 1
        return polyline
    for stop in routed_suffix_stops:
        polyline.append(
            {
                "stop_id": stop.get("id"),
                "order": order,
                "latitude": float(stop.get("latitude") or 0),
                "longitude": float(stop.get("longitude") or 0),
            }
        )
        order += 1
    return polyline



def _ensure_stop_index_is_editable(target_index: int, editable_from_stop_index: int) -> None:
    if target_index < editable_from_stop_index:
        raise ValueError("cannot edit a completed stop")



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
        .where(GuideSession.status.in_([GuideSessionStatus.PENDING, GuideSessionStatus.ACTIVE]))
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

        if current_stop_changed or context.get("last_played_stop_id") not in valid_stop_ids:
            context["last_played_stop_id"] = None

        for transient_key in [
            "last_played_stop_index",
            "last_playback_action",
            "last_playback_updated_at",
            "stop_segment_cursor_by_stop_id",
            "played_segment_indices_by_stop_id",
            "last_refresh_action",
            "last_refresh_at",
        ]:
            context.pop(transient_key, None)

        if current_stop_changed:
            guide_session.playback_state = GuidePlaybackState.NOT_TRIGGERED
            context["playback_state"] = guide_session.playback_state.value
        else:
            context["playback_state"] = guide_session.playback_state.value

        guide_session.itinerary_version_id = new_version_id
        guide_session.context_json = context
