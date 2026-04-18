import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_guide_session_start_and_finish_flow(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-lifecycle",
            "title": "Lifecycle trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {},
        },
    )
    assert session_response.status_code == 201
    guide_session_id = session_response.json()["data"]["id"]
    assert session_response.json()["data"]["status"] == "pending"
    assert session_response.json()["data"]["context"]["trip_state"] == "pending"

    gps_before_start = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    assert gps_before_start.status_code == 200

    start_response = await client.post(f"/api/v1/session/guide/{guide_session_id}/start")
    assert start_response.status_code == 200
    assert start_response.json()["data"]["status"] == "active"

    started_state = await client.get(f"/api/v1/session/guide/{guide_session_id}")
    assert started_state.status_code == 200
    started_context = started_state.json()["data"]["context"]
    assert started_context["trip_state"] == "active"
    assert "trip_started_at" in started_context

    gps_after_start = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    assert gps_after_start.status_code == 200

    finish_response = await client.post(f"/api/v1/session/guide/{guide_session_id}/finish")
    assert finish_response.status_code == 200
    assert finish_response.json()["data"]["status"] == "finished"

    finished_state = await client.get(f"/api/v1/session/guide/{guide_session_id}")
    assert finished_state.status_code == 200
    finished_context = finished_state.json()["data"]["context"]
    assert finished_context["trip_state"] == "finished"
    assert "trip_finished_at" in finished_context
