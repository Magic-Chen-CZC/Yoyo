from __future__ import annotations

from typing import Any

from yoyo.modules.planner.poi_selector import build_stops_from_selected_pois
from yoyo.modules.planner.template_repository import list_route_templates


def build_route_recommendations(preferences: dict[str, Any]) -> list[dict[str, Any]]:
    preferred_tags = {str(tag) for tag in preferences.get("preferred_tags", [])}
    selected_poi_ids = [str(item) for item in preferences.get("selected_poi_ids", [])]
    base_templates = list_route_templates()
    recommendations: list[dict[str, Any]] = []

    for template in base_templates:
        score = len(preferred_tags.intersection(set(template.get("tags", []))))
        recommendations.append(
            {
                "recommendation_id": template["id"],
                "title": template["title"],
                "summary": template["summary"],
                "entry_type": "ai_recommendation",
                "template_id": template["id"],
                "score": score,
                "tags": template.get("tags", []),
            }
        )

    if selected_poi_ids:
        selected_stops = build_stops_from_selected_pois(selected_poi_ids)
        if selected_stops:
            recommendations.append(
                {
                    "recommendation_id": "custom-poi-blend",
                    "title": "Custom POI Blend",
                    "summary": "A recommendation centered on the POIs you highlighted in the short dialogue.",
                    "entry_type": "ai_recommendation",
                    "selected_poi_ids": [str(stop["id"]) for stop in selected_stops],
                    "score": 99,
                    "tags": [str(stop["category"]) for stop in selected_stops],
                }
            )

    recommendations.sort(key=lambda item: (-int(item["score"]), str(item["title"])))
    top_three = recommendations[:3]
    for item in top_three:
        item.pop("score", None)
    return top_three
