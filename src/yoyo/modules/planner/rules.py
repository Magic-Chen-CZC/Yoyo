from typing import Any


DEFAULT_POIS = [
    {
        "id": "stop-tiananmen-square",
        "name": "Tiananmen Square",
        "category": "landmark",
        "latitude": 39.9050,
        "longitude": 116.3976,
        "recommended_duration_minutes": 45,
    },
    {
        "id": "stop-forbidden-city",
        "name": "Forbidden City",
        "category": "museum",
        "latitude": 39.9163,
        "longitude": 116.3972,
        "recommended_duration_minutes": 180,
    },
    {
        "id": "stop-jingshan-park",
        "name": "Jingshan Park",
        "category": "park",
        "latitude": 39.9240,
        "longitude": 116.3967,
        "recommended_duration_minutes": 60,
    },
]


def build_default_plan(preferences: dict[str, Any]) -> dict[str, Any]:
    preferred_poi_count = int(preferences.get("preferred_poi_count", 3) or 3)
    selected_pois = DEFAULT_POIS[: max(1, min(preferred_poi_count, len(DEFAULT_POIS)))]

    return {
        "summary": "Starter Beijing itinerary",
        "pace": preferences.get("travel_pace", "balanced"),
        "stops": selected_pois,
    }
