from httpx import AsyncClient
import pytest

from yoyo.jobs.tasks.guide_generation import run_guide_generation_job


@pytest.mark.asyncio
async def test_guide_asset_and_playback_flow(client: AsyncClient, db_session, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    async def fake_new_session():
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-playback",
            "title": "Playback trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {
                "current_stop_index": 0,
                "current_position": None,
                "last_arrived_stop_id": None,
                "last_played_stop_id": None,
            },
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    job_id = enqueued["job_id"]
    await run_guide_generation_job({}, job_id)

    asset_response = await client.get(f"/api/v1/guide/asset/{guide_session_id}")
    assert asset_response.status_code == 200
    asset_body = asset_response.json()
    assert asset_body["data"]["asset_status"] == "ready"
    assert asset_body["data"]["summary"] == "Starter Beijing itinerary"
    assert asset_body["data"]["playback_state"] == "not_triggered"
    assert asset_body["data"]["result"]["guide_script"]["title"] == "Starter Beijing itinerary"
    assert asset_body["data"]["result"]["card"]["highlights"] == ["Tiananmen Square", "Forbidden City"]
    assert asset_body["data"]["result"]["audio"]["status"] == "not_generated"

    trigger_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "trigger"},
    )
    assert trigger_response.status_code == 200
    assert trigger_response.json()["data"]["playback_state"] == "triggered"

    playback_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "play"},
    )
    assert playback_response.status_code == 200
    playback_body = playback_response.json()
    assert playback_body["data"]["playback_state"] == "playing"

    complete_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "complete"},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["data"]["playback_state"] == "played"

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert current_response.status_code == 200
    current_body = current_response.json()
    assert current_body["data"]["playback_state"] == "played"
