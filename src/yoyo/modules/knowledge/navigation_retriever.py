from __future__ import annotations

from yoyo.modules.integrations.amap.client import AmapRouteClient
from yoyo.modules.knowledge.place_resolver import (
    place_text_has_ambiguity_signal,
    registered_navigation_place_matches,
)
from yoyo.modules.knowledge.schemas import (
    NavigationClarificationCandidate,
    NavigationContext,
    NavigationLeg,
    NavigationPlace,
    NavigationPlaceClarification,
    NavigationSlotPayload,
    NavigationStep,
)


_TRANSIT_EMPTY_FALLBACK_REASON = "transit_empty_use_walking"
_TRANSIT_EMPTY_PROVIDER_REASON = "empty_navigation_payload"


async def get_navigation_context(
    *,
    origin_name: str | None = None,
    destination_name: str | None = None,
    slot_result: NavigationSlotPayload | None = None,
    mode: str | None = None,
) -> NavigationContext:
    client = AmapRouteClient()
    if slot_result is not None:
        route_mode = mode or slot_result.mode
        destinations = [destination for destination in slot_result.destinations if destination]
        if not slot_result.origin or not destinations:
            return NavigationContext(
                origin_name=slot_result.origin,
                destination_name=destinations[0] if destinations else None,
                mode=route_mode,
                requested_mode=route_mode,
                final_mode=route_mode,
                requested_transit_preference=slot_result.transit_preference,
                slot_result=slot_result,
                source="amap",
                status="degraded",
                reason=slot_result.reason or "missing_origin_or_destination",
            )
        if _is_clarification_selection_error(slot_result.reason):
            clarification = _clarification_from_selection_error(slot_result)
            return NavigationContext(
                origin_name=slot_result.origin,
                destination_name=destinations[-1] if destinations else None,
                mode=route_mode,
                requested_mode=route_mode,
                final_mode=route_mode,
                requested_transit_preference=slot_result.transit_preference,
                slot_result=slot_result,
                clarification=clarification,
                source="amap",
                status="clarification",
                reason=clarification.reason,
            )
        clarification = await _build_slot_place_clarification(client, slot_result)
        if clarification is not None:
            return NavigationContext(
                origin_name=slot_result.origin,
                destination_name=destinations[-1] if destinations else None,
                mode=route_mode,
                requested_mode=route_mode,
                final_mode=route_mode,
                requested_transit_preference=slot_result.transit_preference,
                slot_result=slot_result,
                clarification=clarification,
                source="amap",
                status="clarification",
                reason=clarification.reason,
            )
        legs = await _build_navigation_legs(
            client,
            slot_result.origin,
            destinations,
            route_mode,
            origin_place=slot_result.origin_place,
            destination_places=slot_result.destination_places,
            transit_preference=slot_result.transit_preference,
        )
        return _assemble_navigation_context(legs=legs, mode=route_mode, slot_result=slot_result)

    requested_mode = mode or "walking"
    payload = await _get_text_navigation_with_mode_fallback(
        client,
        {
            "origin_name": origin_name,
            "destination_name": destination_name,
            "mode": requested_mode,
        },
        requested_mode,
    )
    steps = _build_navigation_steps(list(payload.get("steps") or []))
    return NavigationContext(
        origin_name=payload.get("origin_name"),
        destination_name=payload.get("destination_name"),
        mode=requested_mode,
        requested_mode=requested_mode,
        final_mode=str(payload.get("_final_mode") or payload.get("mode") or requested_mode),
        requested_transit_preference=payload.get("_requested_transit_preference"),
        final_transit_vehicle_types=list(payload.get("_final_transit_vehicle_types") or []),
        mode_fallback_used=bool(payload.get("_mode_fallback_used")),
        mode_fallback_reason=payload.get("_mode_fallback_reason"),
        distance_meters=payload.get("distance_meters"),
        duration_seconds=payload.get("duration_seconds"),
        steps=steps,
        legs=[
            NavigationLeg(
                origin_name=payload.get("origin_name"),
                destination_name=payload.get("destination_name"),
                requested_mode=payload.get("_requested_mode") or requested_mode,
                provider_mode=payload.get("_provider_mode"),
                final_mode=payload.get("_final_mode") or payload.get("mode") or requested_mode,
                requested_transit_preference=payload.get("_requested_transit_preference"),
                final_transit_vehicle_types=list(payload.get("_final_transit_vehicle_types") or []),
                mode_fallback_used=bool(payload.get("_mode_fallback_used")),
                mode_fallback_reason=payload.get("_mode_fallback_reason"),
                provider_reason=payload.get("_provider_reason"),
                distance_meters=payload.get("distance_meters"),
                duration_seconds=payload.get("duration_seconds"),
                steps=steps,
                status=str(payload.get("status") or "available"),
                reason=payload.get("reason"),
            )
        ]
        if payload.get("origin_name") or payload.get("destination_name")
        else [],
        source=str(payload.get("source") or "amap"),
        status=str(payload.get("status") or "available"),
        reason=payload.get("reason"),
    )


async def _build_navigation_legs(
    client: AmapRouteClient,
    origin_name: str,
    destinations: list[str],
    mode: str,
    *,
    origin_place: NavigationPlace | None = None,
    destination_places: list[NavigationPlace] | None = None,
    transit_preference: str | None = None,
) -> list[NavigationLeg]:
    legs: list[NavigationLeg] = []
    current_origin = origin_name
    current_origin_place = origin_place
    resolved_destination_places = destination_places or []
    for index, destination in enumerate(destinations):
        destination_place = resolved_destination_places[index] if index < len(resolved_destination_places) else None
        origin_request_name = _place_display_name(current_origin_place) or current_origin
        destination_request_name = _place_display_name(destination_place) or destination
        request_kwargs = {
            "origin_name": origin_request_name,
            "destination_name": destination_request_name,
            "mode": mode,
        }
        if mode == "transit" and transit_preference:
            request_kwargs["transit_preference"] = transit_preference
        if origin_location := _place_location(current_origin_place):
            request_kwargs["origin_location"] = origin_location
        if destination_location := _place_location(destination_place):
            request_kwargs["destination_location"] = destination_location
        payload = await _get_text_navigation_with_mode_fallback(client, request_kwargs, mode)
        steps = _build_navigation_steps(list(payload.get("steps") or []))
        legs.append(
            NavigationLeg(
                origin_name=payload.get("origin_name") or origin_request_name,
                destination_name=payload.get("destination_name") or destination_request_name,
                requested_mode=payload.get("_requested_mode") or mode,
                provider_mode=payload.get("_provider_mode"),
                final_mode=payload.get("_final_mode") or payload.get("mode") or mode,
                requested_transit_preference=payload.get("_requested_transit_preference"),
                final_transit_vehicle_types=list(payload.get("_final_transit_vehicle_types") or []),
                mode_fallback_used=bool(payload.get("_mode_fallback_used")),
                mode_fallback_reason=payload.get("_mode_fallback_reason"),
                provider_reason=payload.get("_provider_reason"),
                distance_meters=payload.get("distance_meters"),
                duration_seconds=payload.get("duration_seconds"),
                steps=steps,
                status=str(payload.get("status") or "available"),
                reason=payload.get("reason"),
            )
        )
        current_origin = destination_request_name
        current_origin_place = destination_place
    return legs


async def _get_text_navigation_with_mode_fallback(
    client: AmapRouteClient,
    request_kwargs: dict,
    requested_mode: str,
) -> dict:
    payload = await client.get_text_navigation(**request_kwargs)
    requested_transit_preference = request_kwargs.get("transit_preference")
    payload["_requested_mode"] = requested_mode
    payload["_provider_mode"] = str(payload.get("mode") or requested_mode)
    payload["_final_mode"] = str(payload.get("mode") or requested_mode)
    payload["_requested_transit_preference"] = requested_transit_preference
    payload["_final_transit_vehicle_types"] = list(payload.get("vehicle_types") or [])
    payload["_mode_fallback_used"] = False
    payload["_mode_fallback_reason"] = None
    payload["_provider_reason"] = payload.get("reason")
    if requested_mode != "transit" or payload.get("reason") != _TRANSIT_EMPTY_PROVIDER_REASON:
        return payload

    walking_kwargs = {**request_kwargs, "mode": "walking"}
    walking_payload = await client.get_text_navigation(**walking_kwargs)
    walking_payload["_requested_mode"] = requested_mode
    walking_payload["_provider_mode"] = "transit"
    walking_payload["_final_mode"] = "walking"
    walking_payload["_requested_transit_preference"] = requested_transit_preference
    walking_payload["_final_transit_vehicle_types"] = []
    walking_payload["_mode_fallback_used"] = True
    walking_payload["_mode_fallback_reason"] = _TRANSIT_EMPTY_FALLBACK_REASON
    walking_payload["_provider_reason"] = _TRANSIT_EMPTY_PROVIDER_REASON
    return walking_payload


def _assemble_navigation_context(
    *,
    legs: list[NavigationLeg],
    mode: str,
    slot_result: NavigationSlotPayload,
) -> NavigationContext:
    total_distance = sum(leg.distance_meters or 0 for leg in legs) or None
    total_duration = sum(leg.duration_seconds or 0 for leg in legs) or None
    all_steps = [step for leg in legs for step in leg.steps]
    degraded_leg = next((leg for leg in legs if leg.status != "available"), None)
    mode_fallback_used = any(leg.mode_fallback_used for leg in legs)
    final_mode = _aggregate_final_mode(legs, mode)
    return NavigationContext(
        origin_name=legs[0].origin_name if legs else slot_result.origin,
        destination_name=legs[-1].destination_name if legs else (slot_result.destinations[-1] if slot_result.destinations else None),
        mode=mode,
        requested_mode=mode,
        final_mode=final_mode,
        requested_transit_preference=slot_result.transit_preference,
        final_transit_vehicle_types=_aggregate_transit_vehicle_types(legs),
        mode_fallback_used=mode_fallback_used,
        mode_fallback_reason=_TRANSIT_EMPTY_FALLBACK_REASON if mode_fallback_used else None,
        distance_meters=total_distance,
        duration_seconds=total_duration,
        steps=all_steps,
        legs=legs,
        slot_result=slot_result,
        source="amap",
        status=degraded_leg.status if degraded_leg else "available",
        reason=degraded_leg.reason if degraded_leg else None,
    )


def _aggregate_final_mode(legs: list[NavigationLeg], requested_mode: str) -> str:
    final_modes = {leg.final_mode for leg in legs if leg.final_mode}
    if not final_modes:
        return requested_mode
    if len(final_modes) == 1:
        return next(iter(final_modes)) or requested_mode
    return "mixed"


def _aggregate_transit_vehicle_types(legs: list[NavigationLeg]) -> list[str]:
    vehicle_types: list[str] = []
    for leg in legs:
        for vehicle_type in leg.final_transit_vehicle_types:
            if vehicle_type not in vehicle_types:
                vehicle_types.append(vehicle_type)
    return vehicle_types


def _build_navigation_steps(raw_steps: list[dict]) -> list[NavigationStep]:
    return [
        NavigationStep(
            instruction=str(step.get("instruction") or ""),
            road=step.get("road"),
            orientation=step.get("orientation"),
            distance_meters=step.get("distance_meters"),
            duration_seconds=step.get("duration_seconds"),
            action=step.get("action"),
            assistant_action=step.get("assistant_action"),
            polyline=step.get("polyline"),
            end_location=step.get("end_location"),
            turn_location_text=step.get("turn_location_text"),
            vehicle_type=step.get("vehicle_type"),
        )
        for step in raw_steps
        if step.get("instruction")
    ]


def _place_location(place: NavigationPlace | None) -> tuple[float, float] | None:
    if place is None or place.longitude is None or place.latitude is None:
        return None
    return place.longitude, place.latitude


def _place_display_name(place: NavigationPlace | None) -> str | None:
    if place is None:
        return None
    return place.display_name or place.raw_text or place.name


def _is_clarification_selection_error(reason: str | None) -> bool:
    if not reason:
        return False
    return (
        reason == "ambiguous_middle_selection"
        or reason == "clarification_fallback_needs_clarification"
        or reason.startswith("selection_index_out_of_range")
    )


def _clarification_from_selection_error(slot_result: NavigationSlotPayload) -> NavigationPlaceClarification:
    reason = slot_result.reason or "selection_index_out_of_range"
    message = "我还不能确定你选的是哪一个，请直接回复候选编号。"
    if reason == "ambiguous_middle_selection":
        message = "中间有两个候选，我还不能确定你指哪一个。请直接回复具体编号。"
    elif reason == "clarification_fallback_needs_clarification":
        message = "我还不能确定你要选哪一个地点，请直接回复候选编号或完整地点名称。"
    elif reason.startswith("selection_index_out_of_range"):
        parts = reason.split(":")
        selected_index = parts[1] if len(parts) > 1 and parts[1] != "None" else None
        candidate_count = parts[2] if len(parts) > 2 and parts[2] != "None" else None
        if selected_index and candidate_count:
            message = f"当前只有 {candidate_count} 个候选，没有第 {selected_index} 个。请重新选择候选编号。"
    return NavigationPlaceClarification(
        raw_text=slot_result.destinations[0] if slot_result.destinations else slot_result.origin,
        target_role="destination",
        target_index=0,
        reason="clarification_selection_error",
        message=message,
        candidates=[],
        slot_result=slot_result.model_dump(),
    )


async def _build_slot_place_clarification(
    client: AmapRouteClient,
    slot_result: NavigationSlotPayload,
) -> NavigationPlaceClarification | None:
    if slot_result.origin_place is not None:
        clarification = await _build_place_clarification(
            client,
            slot_result=slot_result,
            place=slot_result.origin_place,
            target_role="origin",
            target_index=0,
        )
        if clarification is not None:
            return clarification

    for index, destination_place in enumerate(slot_result.destination_places):
        clarification = await _build_place_clarification(
            client,
            slot_result=slot_result,
            place=destination_place,
            target_role="destination",
            target_index=index,
        )
        if clarification is not None:
            return clarification
    return None


async def _build_place_clarification(
    client: AmapRouteClient,
    *,
    slot_result: NavigationSlotPayload,
    place: NavigationPlace,
    target_role: str,
    target_index: int,
) -> NavigationPlaceClarification | None:
    if place.source not in {"geocode_candidate", "unresolved"}:
        return None
    raw_text = place.raw_text or place.display_name or place.name
    if not raw_text:
        return None

    registered_candidates = [
        _candidate_from_navigation_place(candidate, index=0)
        for candidate in registered_navigation_place_matches(raw_text)
    ]
    amap_candidates = [
        _candidate_from_amap_candidate(candidate, index=0)
        for candidate in await client.search_place_candidates(raw_text, limit=5)
    ]
    candidates = _dedupe_clarification_candidates([*registered_candidates, *amap_candidates])
    has_ambiguity_signal = place.reason == "registered_alias_with_ambiguity_signal" or place_text_has_ambiguity_signal(raw_text)
    if not has_ambiguity_signal and len(candidates) < 2:
        return None
    if not candidates and not has_ambiguity_signal:
        return None
    indexed_candidates = [
        candidate.model_copy(update={"index": index})
        for index, candidate in enumerate(candidates[:5], start=1)
    ]
    return NavigationPlaceClarification(
        raw_text=raw_text,
        target_role=target_role,  # type: ignore[arg-type]
        target_index=target_index,
        reason="commercial_or_address_ambiguity" if has_ambiguity_signal else "multiple_amap_candidates",
        message=None,
        candidates=indexed_candidates,
        slot_result=slot_result.model_dump(),
    )


def _candidate_from_navigation_place(place: NavigationPlace, *, index: int) -> NavigationClarificationCandidate:
    return NavigationClarificationCandidate(
        index=index,
        raw_text=place.raw_text,
        place_id=place.place_id,
        name=place.name or place.display_name or place.raw_text or "未知地点",
        display_name=place.display_name or place.name,
        address=None,
        district=None,
        poi_type="景点/旅游POI",
        latitude=place.latitude,
        longitude=place.longitude,
        adcode=place.adcode,
        source="registry",
        confidence=place.confidence,
        reason=place.reason,
    )


def _candidate_from_amap_candidate(candidate: dict[str, object], *, index: int) -> NavigationClarificationCandidate:
    return NavigationClarificationCandidate(
        index=index,
        raw_text=str(candidate.get("name") or ""),
        place_id=None,
        name=str(candidate.get("name") or "未知地点"),
        display_name=str(candidate.get("display_name") or candidate.get("name") or "未知地点"),
        address=str(candidate.get("address") or "") or None,
        district=str(candidate.get("district") or "") or None,
        poi_type=str(candidate.get("poi_type") or "") or None,
        latitude=_optional_float(candidate.get("latitude")),
        longitude=_optional_float(candidate.get("longitude")),
        adcode=str(candidate.get("adcode") or "") or None,
        source="amap_candidate",
        confidence=_optional_float(candidate.get("confidence")) or 0.7,
        reason=str(candidate.get("reason") or "amap_place_text_candidate"),
    )


def _dedupe_clarification_candidates(
    candidates: list[NavigationClarificationCandidate],
) -> list[NavigationClarificationCandidate]:
    deduped: list[NavigationClarificationCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        key = (
            (candidate.display_name or candidate.name).strip().lower(),
            (candidate.address or "").strip().lower(),
            (candidate.adcode or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _optional_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
