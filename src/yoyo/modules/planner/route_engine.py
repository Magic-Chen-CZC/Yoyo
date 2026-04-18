from __future__ import annotations

from typing import Any

from yoyo.modules.integrations.amap.client import AmapRouteClient


async def apply_route_engine(
    plan: dict[str, Any],
    *,
    reorder_stops: bool,
) -> dict[str, Any]:
    route_plan = dict(plan)
    stops = [dict(stop) for stop in route_plan.get("stops", [])]
    if reorder_stops:
        stops = sorted(
            stops,
            key=lambda stop: (
                float(stop.get("latitude") or 0),
                float(stop.get("longitude") or 0),
                str(stop.get("name") or ""),
            ),
        )

    client = AmapRouteClient()
    route_result = await client.build_route(stops)
    existing_meta = dict(route_plan.get("route_meta") or {})
    route_meta = dict(route_result.get("route_meta") or {})
    if route_meta.get("degraded"):
        route_meta["waypoint_order_source"] = existing_meta.get("waypoint_order_source")
    route_plan["stops"] = [dict(stop) for stop in route_result.get("stops", stops)]
    route_plan["polyline"] = list(route_result.get("polyline") or [])
    route_plan["route_meta"] = {
        **existing_meta,
        **route_meta,
    }
    return route_plan
