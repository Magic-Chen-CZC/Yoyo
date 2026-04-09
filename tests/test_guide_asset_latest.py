from httpx import AsyncClient
import pytest

from yoyo.jobs.tasks.guide_generation import run_guide_generation_job


@pytest.mark.asyncio
async def test_active_guide_asset_uses_latest_successful_job(client: AsyncClient, db_session, monkeypatch) -> None:
    enqueued: list[str] = []

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued.append(job_id)

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.guide.service.get_job_pool", fake_get_job_pool)

    async def fake_new_session():
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-latest",
            "title": "Latest guide asset trip",
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

    first_job_id = enqueued[0]
    await run_guide_generation_job({}, first_job_id)

    await client.post(
        "/api/v1/guide/jobs",
        json={
            "itinerary_version_id": itinerary_data["version"]["id"],
            "payload": {"requested_by": "test"},
        },
    )
    second_job_id = enqueued[-1]
    await run_guide_generation_job({}, second_job_id)

    asset_response = await client.get(f"/api/v1/guide/asset/{guide_session_id}")
    assert asset_response.status_code == 200
    body = asset_response.json()
    assert body["data"]["asset_status"] == "ready"
    assert body["data"]["result"]["summary"] == "Starter Beijing itinerary"
    assert body["data"]["result"]["card"]["headline"] == "Starter Beijing itinerary"
