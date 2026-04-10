from math import asin, cos, radians, sin, sqrt
from typing import Any

DEFAULT_ARRIVAL_THRESHOLD_METERS = 200.0
EARTH_RADIUS_METERS = 6_371_000.0


def get_runtime_context(context_json: dict[str, Any] | None) -> dict[str, Any]:
    context = dict(context_json or {})
    context["current_stop_index"] = normalize_stop_index(context.get("current_stop_index"))
    context.setdefault("current_position", None)
    context.setdefault("last_arrived_stop_id", None)
    context.setdefault("last_played_stop_id", None)
    return context


def normalize_stop_index(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def clamp_stop_index(index: int, stop_count: int) -> int:
    if stop_count <= 0:
        return 0
    return max(0, min(index, stop_count - 1))


def get_stops(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    stops = (plan or {}).get("stops", [])
    return [dict(stop) for stop in stops]


def get_current_stop_index(context_json: dict[str, Any] | None, stop_count: int) -> int:
    return clamp_stop_index(
        normalize_stop_index((context_json or {}).get("current_stop_index")),
        stop_count,
    )


def get_current_and_next_stop(
    stops: list[dict[str, Any]],
    current_stop_index: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not stops:
        return None, None

    current_stop = stops[current_stop_index]
    next_stop = stops[current_stop_index + 1] if current_stop_index + 1 < len(stops) else None
    return current_stop, next_stop


def get_arrival_threshold_meters(stop: dict[str, Any] | None) -> float | None:
    if stop is None:
        return None

    threshold = stop.get("arrival_threshold_meters", DEFAULT_ARRIVAL_THRESHOLD_METERS)
    try:
        return float(threshold)
    except (TypeError, ValueError):
        return DEFAULT_ARRIVAL_THRESHOLD_METERS


def distance_to_stop_meters(
    current_position: dict[str, float] | None,
    stop: dict[str, Any] | None,
) -> float | None:
    if current_position is None or stop is None:
        return None

    try:
        latitude_1 = float(current_position["latitude"])
        longitude_1 = float(current_position["longitude"])
        latitude_2 = float(stop["latitude"])
        longitude_2 = float(stop["longitude"])
    except (KeyError, TypeError, ValueError):
        return None

    return haversine_distance_meters(latitude_1, longitude_1, latitude_2, longitude_2)


def haversine_distance_meters(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    latitude_delta = radians(latitude_2 - latitude_1)
    longitude_delta = radians(longitude_2 - longitude_1)
    origin_latitude = radians(latitude_1)
    destination_latitude = radians(latitude_2)

    a = (
        sin(latitude_delta / 2) ** 2
        + cos(origin_latitude) * cos(destination_latitude) * sin(longitude_delta / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_METERS * c


def remap_current_stop_index(
    old_stops: list[dict[str, Any]],
    new_stops: list[dict[str, Any]],
    current_stop_index: int,
) -> tuple[int, bool]:
    if not new_stops:
        return 0, True

    old_index = clamp_stop_index(current_stop_index, len(old_stops))
    old_current_stop = old_stops[old_index] if old_stops else None
    old_current_stop_id = old_current_stop.get("id") if old_current_stop else None

    if old_current_stop_id is not None:
        for index, stop in enumerate(new_stops):
            if stop.get("id") == old_current_stop_id:
                return index, False

    new_index = clamp_stop_index(old_index, len(new_stops))
    new_current_stop = new_stops[new_index]
    current_stop_changed = old_current_stop_id != new_current_stop.get("id")
    return new_index, current_stop_changed
