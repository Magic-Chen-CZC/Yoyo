from typing import Any

from yoyo.modules.planner.stop_catalog import CANONICAL_STOPS, clone_stops


def build_default_plan(preferences: dict[str, Any]) -> dict[str, Any]:
    preferred_poi_count = int(preferences.get("preferred_poi_count", 3) or 3)
    selected_pois = clone_stops(
        CANONICAL_STOPS[: max(1, min(preferred_poi_count, len(CANONICAL_STOPS)))]
    )

    return {
        "summary": "Starter Beijing itinerary",
        "pace": preferences.get("travel_pace", "balanced"),
        "stops": selected_pois,
    }
