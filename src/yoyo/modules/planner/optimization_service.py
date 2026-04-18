from __future__ import annotations

from math import hypot
from typing import Any


def apply_route_optimization(
    plan: dict[str, Any],
    *,
    source: str,
    reorder_stops: bool = False,
) -> dict[str, Any]:
    optimized_plan = dict(plan)
    stops = [dict(stop) for stop in optimized_plan.get("stops", [])]
    if reorder_stops and len(stops) > 1:
        stops = sorted(
            stops,
            key=lambda stop: (
                _distance_key(stop),
                str(stop.get("name") or ""),
            ),
        )
    optimized_plan["stops"] = stops
    optimized_plan["route_meta"] = {
        **dict(optimized_plan.get("route_meta") or {}),
        "optimization_status": "optimized",
        "routing_provider": None,
        "waypoint_order_source": source,
    }
    return optimized_plan


def _distance_key(stop: dict[str, Any]) -> float:
    latitude = float(stop.get("latitude") or 0)
    longitude = float(stop.get("longitude") or 0)
    return hypot(latitude, longitude)


def _distance_key(stop: dict[str, Any]) -> float:
    latitude = float(stop.get("latitude") or 0)
    longitude = float(stop.get("longitude") or 0)
    return hypot(latitude, longitude)
