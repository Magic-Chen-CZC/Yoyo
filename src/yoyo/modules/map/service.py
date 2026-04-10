from yoyo.modules.map.schemas import (
    MapMarkerRead,
    MapPolylinePointRead,
    MapSessionRead,
    NavigationSummaryRead,
)
from yoyo.modules.session.runtime import get_current_and_next_stop, get_current_stop_index


def build_map_payload(
    guide_session_id: str,
    stops: list[dict],
    current_position: dict[str, float] | None,
    current_stop_index: int,
) -> MapSessionRead:
    normalized_current_stop_index = get_current_stop_index(
        {"current_stop_index": current_stop_index},
        len(stops),
    )
    current_stop_payload, next_stop_payload = get_current_and_next_stop(
        stops,
        normalized_current_stop_index,
    )

    markers: list[MapMarkerRead] = []
    polyline: list[MapPolylinePointRead] = []
    for index, stop in enumerate(stops):
        latitude = float(stop["latitude"])
        longitude = float(stop["longitude"])
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
            )
        )
        polyline.append(
            MapPolylinePointRead(
                stop_id=stop.get("id"),
                order=index,
                latitude=latitude,
                longitude=longitude,
            )
        )

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
            has_next_stop=next_stop is not None,
        ),
        current_position=current_position,
        current_stop=current_stop,
        next_stop=next_stop,
    )
