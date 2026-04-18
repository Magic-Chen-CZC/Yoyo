import pytest

from yoyo.modules.integrations.amap.client import AmapRouteClient
from yoyo.modules.planner.route_engine import apply_route_engine


@pytest.mark.asyncio
async def test_amap_client_returns_degraded_route_without_key() -> None:
    client = AmapRouteClient(api_key=None)
    route = await client.build_route(
        [
            {"id": "stop-b", "name": "B", "latitude": 39.92, "longitude": 116.40},
            {"id": "stop-a", "name": "A", "latitude": 39.90, "longitude": 116.39},
        ]
    )
    assert route["route_meta"]["degraded"] is True
    assert route["route_meta"]["routing_provider"] is None
    assert len(route["polyline"]) == 2


@pytest.mark.asyncio
async def test_route_engine_preserves_waypoint_source_on_degraded_route() -> None:
    plan = {
        "summary": "demo",
        "stops": [
            {"id": "stop-b", "name": "B", "latitude": 39.92, "longitude": 116.40},
            {"id": "stop-a", "name": "A", "latitude": 39.90, "longitude": 116.39},
        ],
        "route_meta": {
            "optimization_status": "optimized",
            "routing_provider": None,
            "waypoint_order_source": "manual_selection",
        },
    }
    result = await apply_route_engine(plan, reorder_stops=True)
    assert result["route_meta"]["waypoint_order_source"] == "manual_selection"
    assert result["route_meta"]["degraded"] is True
    assert [stop["id"] for stop in result["stops"]] == ["stop-a", "stop-b"]
