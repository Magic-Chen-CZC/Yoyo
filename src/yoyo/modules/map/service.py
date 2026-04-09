from yoyo.modules.map.schemas import MapSessionRead


def build_map_payload(
    guide_session_id: str,
    stops: list[dict],
    current_position: dict[str, float] | None,
) -> MapSessionRead:
    markers = []
    polyline = []
    for index, stop in enumerate(stops):
        latitude = float(stop.get("latitude", 39.90 + index * 0.01))
        longitude = float(stop.get("longitude", 116.39 + index * 0.01))
        markers.append(
            {
                "name": stop.get("name"),
                "latitude": latitude,
                "longitude": longitude,
                "category": stop.get("category"),
            }
        )
        polyline.append({"latitude": latitude, "longitude": longitude})

    current_stop = markers[0] if markers else None
    next_stop = markers[1] if len(markers) > 1 else None

    return MapSessionRead(
        guide_session_id=guide_session_id,
        markers=markers,
        polyline=polyline,
        current_position=current_position,
        current_stop=current_stop,
        next_stop=next_stop,
    )
