from __future__ import annotations

from typing import Any

from yoyo.modules.planner.poi_selector import build_stops_from_selected_pois
from yoyo.modules.planner.rules import build_default_plan
from yoyo.modules.planner.template_repository import build_stops_from_template, get_route_template


def build_plan_from_entry(
    *,
    entry_type: str,
    preferences: dict[str, Any],
    template_id: str | None,
    selected_poi_ids: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if entry_type == "template":
        template = get_route_template(template_id)
        if template is None:
            raise ValueError("template route not found")
        stops = build_stops_from_template(template_id)
        return (
            {
                "summary": template["title"],
                "pace": template["pace"],
                "entry_type": entry_type,
                "template_id": template["id"],
                "route_meta": {
                    "optimization_status": "not_started",
                    "routing_provider": None,
                    "waypoint_order_source": "template",
                },
                "stops": stops,
            },
            {"template_id": template["id"], "selected_poi_ids": [stop["id"] for stop in stops]},
        )

    if entry_type == "manual_poi":
        stops = build_stops_from_selected_pois(selected_poi_ids)
        if not stops:
            raise ValueError("selected_poi_ids is required for manual_poi entry")
        return (
            {
                "summary": "Custom selected Beijing route",
                "pace": preferences.get("travel_pace", "balanced"),
                "entry_type": entry_type,
                "template_id": None,
                "route_meta": {
                    "optimization_status": "not_started",
                    "routing_provider": None,
                    "waypoint_order_source": "manual_selection",
                },
                "stops": stops,
            },
            {"template_id": None, "selected_poi_ids": [stop["id"] for stop in stops]},
        )

    if entry_type == "ai_recommendation_selected":
        recommendation_template_id = template_id or str(preferences.get("recommendation_template_id") or "")
        recommendation_selected_ids = selected_poi_ids or [
            str(item) for item in preferences.get("recommendation_selected_poi_ids", [])
        ]
        if recommendation_selected_ids:
            stops = build_stops_from_selected_pois(recommendation_selected_ids)
            if not stops:
                raise ValueError("recommendation_selected_poi_ids did not match known POIs")
            return (
                {
                    "summary": "AI recommended Beijing route",
                    "pace": preferences.get("travel_pace", "balanced"),
                    "entry_type": entry_type,
                    "template_id": None,
                    "route_meta": {
                        "optimization_status": "not_started",
                        "routing_provider": None,
                        "waypoint_order_source": "ai_recommendation",
                    },
                    "stops": stops,
                },
                {"template_id": None, "selected_poi_ids": [stop["id"] for stop in stops]},
            )
        if recommendation_template_id:
            template = get_route_template(recommendation_template_id)
            if template is None:
                raise ValueError("recommended template route not found")
            stops = build_stops_from_template(recommendation_template_id)
            return (
                {
                    "summary": template["title"],
                    "pace": template["pace"],
                    "entry_type": entry_type,
                    "template_id": template["id"],
                    "route_meta": {
                        "optimization_status": "not_started",
                        "routing_provider": None,
                        "waypoint_order_source": "ai_recommendation",
                    },
                    "stops": stops,
                },
                {"template_id": template["id"], "selected_poi_ids": [stop["id"] for stop in stops]},
            )
        raise ValueError("ai_recommendation_selected requires a template_id or selected_poi_ids")

    fallback_plan = build_default_plan(preferences)
    fallback_plan["entry_type"] = "starter_default"
    fallback_plan["template_id"] = None
    fallback_plan["route_meta"] = {
        "optimization_status": "not_started",
        "routing_provider": None,
        "waypoint_order_source": "default",
    }
    return fallback_plan, {"template_id": None, "selected_poi_ids": [stop.get("id") for stop in fallback_plan.get("stops", [])]}
