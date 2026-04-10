from typing import Any

CANONICAL_STOPS: list[dict[str, Any]] = [
    {
        "id": "stop-tiananmen-square",
        "name": "Tiananmen Square",
        "category": "landmark",
        "latitude": 39.9050,
        "longitude": 116.3976,
        "recommended_duration_minutes": 45,
        "arrival_threshold_meters": 200,
    },
    {
        "id": "stop-forbidden-city",
        "name": "Forbidden City",
        "category": "museum",
        "latitude": 39.9163,
        "longitude": 116.3972,
        "recommended_duration_minutes": 180,
        "arrival_threshold_meters": 200,
    },
    {
        "id": "stop-jingshan-park",
        "name": "Jingshan Park",
        "category": "park",
        "latitude": 39.9240,
        "longitude": 116.3967,
        "recommended_duration_minutes": 60,
        "arrival_threshold_meters": 200,
    },
]


def clone_stop(stop: dict[str, Any]) -> dict[str, Any]:
    return dict(stop)


def clone_stops(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [clone_stop(stop) for stop in stops]


def get_canonical_stop(
    *, stop_id: str | None = None, stop_name: str | None = None
) -> dict[str, Any] | None:
    if stop_id is not None:
        for stop in CANONICAL_STOPS:
            if stop["id"] == stop_id:
                return clone_stop(stop)

    if stop_name is not None:
        lowered_name = stop_name.strip().lower()
        for stop in CANONICAL_STOPS:
            if str(stop["name"]).lower() == lowered_name:
                return clone_stop(stop)

    return None
