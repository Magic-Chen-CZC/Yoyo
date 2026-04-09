from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_session_current_map_and_gps_flow(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-map",
            "title": "Map trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert current_response.status_code == 200
    current_body = current_response.json()
    assert current_body["data"]["stop_count"] == 2
    assert current_body["data"]["playback_state"] == "not_triggered"
    assert current_body["data"]["current_stop"]["name"] == "Tiananmen Square"
    assert current_body["data"]["current_stop"]["id"] == "stop-tiananmen-square"
    assert current_body["data"]["current_stop"]["latitude"] == 39.905
    assert current_body["data"]["current_stop"]["longitude"] == 116.3976

    map_response = await client.get(f"/api/v1/map/session/{guide_session_id}")
    assert map_response.status_code == 200
    map_body = map_response.json()
    assert len(map_body["data"]["markers"]) == 2
    assert map_body["data"]["current_stop"]["name"] == "Tiananmen Square"

    gps_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9042, "longitude": 116.4074},
    )
    assert gps_response.status_code == 200
    gps_body = gps_response.json()
    assert gps_body["data"]["arrived"] is True
    assert gps_body["data"]["current_position"] == {
        "latitude": 39.9042,
        "longitude": 116.4074,
    }

    current_after_gps_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert current_after_gps_response.status_code == 200
    current_after_gps_body = current_after_gps_response.json()
    assert current_after_gps_body["data"]["playback_state"] == "triggered"
