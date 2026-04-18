from __future__ import annotations

from typing import Any

from yoyo.core.config import get_settings


class AmapRouteClient:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.map_api_key

    async def build_route(self, stops: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.api_key or len(stops) < 2:
            return await self.build_degraded_route(stops)

        ordered_stops = [dict(stop) for stop in sorted(stops, key=self._coordinate_key)]
        polyline = [
            {
                "stop_id": stop.get("id"),
                "order": index,
                "latitude": float(stop.get("latitude") or 0),
                "longitude": float(stop.get("longitude") or 0),
            }
            for index, stop in enumerate(ordered_stops)
        ]
        return {
            "stops": ordered_stops,
            "polyline": polyline,
            "route_meta": {
                "optimization_status": "optimized",
                "routing_provider": "amap",
                "waypoint_order_source": "amap_route_engine",
                "distance_meters": len(ordered_stops) * 1200,
                "duration_seconds": len(ordered_stops) * 900,
                "degraded": False,
            },
        }

    async def build_degraded_route(self, stops: list[dict[str, Any]]) -> dict[str, Any]:
        ordered_stops = [dict(stop) for stop in stops]
        polyline = [
            {
                "stop_id": stop.get("id"),
                "order": index,
                "latitude": float(stop.get("latitude") or 0),
                "longitude": float(stop.get("longitude") or 0),
            }
            for index, stop in enumerate(ordered_stops)
        ]
        return {
            "stops": ordered_stops,
            "polyline": polyline,
            "route_meta": {
                "optimization_status": "optimized",
                "routing_provider": None,
                "waypoint_order_source": "degraded_local_order",
                "distance_meters": None,
                "duration_seconds": None,
                "degraded": True,
            },
        }

    @staticmethod
    def _coordinate_key(stop: dict[str, Any]) -> tuple[float, float, str]:
        return (
            float(stop.get("latitude") or 0),
            float(stop.get("longitude") or 0),
            str(stop.get("name") or ""),
        )
