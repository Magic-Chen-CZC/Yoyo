from yoyo.modules.map.schemas import (
    MapMarkerRead,
    MapPolylinePointRead,
    MapSessionRead,
    NavigationSummaryRead,
)
from yoyo.modules.session.runtime import (
    get_completed_stop_count,
    get_current_and_next_stop,
    get_current_stop_index,
    get_editable_from_stop_index,
)


def build_map_payload(
    guide_session_id: str,
    stops: list[dict],
    current_position: dict[str, float] | None,
    current_stop_index: int,
    stop_summaries: dict[str, dict[str, object]] | None = None,
    comment_summaries: dict[str, dict[str, object]] | None = None,
    route_polyline: list[dict[str, object]] | None = None,
) -> MapSessionRead:
    normalized_current_stop_index = get_current_stop_index(
        {"current_stop_index": current_stop_index},
        len(stops),
    )
    editable_from_stop_index = get_editable_from_stop_index(normalized_current_stop_index, len(stops))
    current_stop_payload, next_stop_payload = get_current_and_next_stop(
        stops,
        editable_from_stop_index,
    )

    stop_summaries = stop_summaries or {}
    comment_summaries = comment_summaries or {}
    route_polyline = route_polyline or []
    completed_stop_count = get_completed_stop_count(normalized_current_stop_index, len(stops))
    markers: list[MapMarkerRead] = []
    polyline: list[MapPolylinePointRead] = []
    for index, stop in enumerate(stops):
        latitude = float(stop["latitude"])
        longitude = float(stop["longitude"])
        stop_id = str(stop.get("id") or "")
        summary = dict(stop_summaries.get(stop_id) or {})
        comment_summary = dict(comment_summaries.get(stop_id) or {})
        markers.append(
            MapMarkerRead(
                id=stop.get("id"),
                name=stop.get("name"),
                category=stop.get("category"),
                latitude=latitude,
                longitude=longitude,
                order=index,
                is_current=current_stop_payload is not None
                and stop.get("id") == current_stop_payload.get("id"),
                is_next=next_stop_payload is not None
                and stop.get("id") == next_stop_payload.get("id"),
                is_completed=index < completed_stop_count,
                is_editable=index >= editable_from_stop_index,
                short_intro=summary.get("short_intro"),
                highlights=list(summary.get("highlights") or []),
                visitor_tip=summary.get("visitor_tip"),
                source_type=summary.get("source_type"),
                comment_count=int(comment_summary.get("comment_count") or 0),
                latest_comment_preview=comment_summary.get("latest_comment_preview"),
            )
        )
        if not route_polyline:
            polyline.append(
                MapPolylinePointRead(
                    stop_id=stop.get("id"),
                    order=index,
                    latitude=latitude,
                    longitude=longitude,
                )
            )

    if route_polyline:
        polyline = [
            MapPolylinePointRead(
                stop_id=item.get("stop_id"),
                order=int(item.get("order") or 0),
                latitude=float(item.get("latitude") or 0),
                longitude=float(item.get("longitude") or 0),
            )
            for item in route_polyline
        ]

    current_stop = next((marker for marker in markers if marker.is_current), None)
    next_stop = next((marker for marker in markers if marker.is_next), None)
    stop_count = len(stops)

    return MapSessionRead(
        guide_session_id=guide_session_id,
        markers=markers,
        polyline=polyline,
        navigation_summary=NavigationSummaryRead(
            current_stop_index=normalized_current_stop_index,
            stop_count=stop_count,
            remaining_stop_count=max(stop_count - normalized_current_stop_index - 1, 0),
            completed_stop_count=completed_stop_count,
            editable_from_stop_index=editable_from_stop_index,
            has_next_stop=next_stop is not None,
        ),
        current_position=current_position,
        current_stop=current_stop,
        next_stop=next_stop,
    )
