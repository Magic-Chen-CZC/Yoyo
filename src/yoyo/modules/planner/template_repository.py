from __future__ import annotations

from copy import deepcopy
from typing import Any

from yoyo.modules.planner.stop_catalog import CANONICAL_STOPS

ROUTE_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "classic-central-beijing",
        "title": "Classic Central Beijing",
        "summary": "A classic first-day route through Beijing landmarks.",
        "pace": "balanced",
        "tags": ["history", "landmark", "first_visit"],
        "stop_ids": [
            "stop-tiananmen-square",
            "stop-forbidden-city",
            "stop-jingshan-park",
        ],
    },
    {
        "id": "imperial-highlights",
        "title": "Imperial Highlights",
        "summary": "A focused route around imperial Beijing history.",
        "pace": "focused",
        "tags": ["history", "architecture"],
        "stop_ids": [
            "stop-forbidden-city",
            "stop-jingshan-park",
        ],
    },
    {
        "id": "relaxed-view-route",
        "title": "Relaxed View Route",
        "summary": "A lighter route with open spaces and city views.",
        "pace": "relaxed",
        "tags": ["views", "relaxed", "photography"],
        "stop_ids": [
            "stop-tiananmen-square",
            "stop-jingshan-park",
        ],
    },
]

STOP_BY_ID = {stop["id"]: stop for stop in CANONICAL_STOPS}


def list_route_templates() -> list[dict[str, Any]]:
    return [deepcopy(template) for template in ROUTE_TEMPLATES]


def get_route_template(template_id: str | None) -> dict[str, Any] | None:
    if template_id is None:
        return None
    for template in ROUTE_TEMPLATES:
        if template["id"] == template_id:
            return deepcopy(template)
    return None


def build_stops_from_template(template_id: str | None) -> list[dict[str, Any]]:
    template = get_route_template(template_id)
    if template is None:
        return []
    return [deepcopy(STOP_BY_ID[stop_id]) for stop_id in template["stop_ids"] if stop_id in STOP_BY_ID]
