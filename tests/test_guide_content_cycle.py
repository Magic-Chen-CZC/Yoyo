from pathlib import Path

import pytest
from httpx import AsyncClient

from yoyo.jobs.tasks.guide_generation import run_guide_generation_job


@pytest.mark.asyncio
async def test_cycle_content_cycles_within_same_stop_without_advancing_route(
    client: AsyncClient, db_session, monkeypatch
) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    async def fake_new_session():
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={"user_id": "user-cycle", "title": "Cycle trip", "preferences": {"preferred_poi_count": 2}},
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

    await run_guide_generation_job({}, enqueued["job_id"])

    first_response = await client.post(
        f"/api/v1/guide/content/{guide_session_id}",
        json={"action": "cycle_content"},
    )
    assert first_response.status_code == 200
    first = first_response.json()["data"]
    assert first["segments"]
    assert first["segment_count"] >= 10
    assert first["more_content_available"] is True
    assert "audio_segments" in first
    assert len(first["audio_segments"]) == len(first["segments"])
    assert {item["status"] for item in first["audio_segments"]} <= {"unavailable", "ready"}

    second_response = await client.post(
        f"/api/v1/guide/content/{guide_session_id}",
        json={"action": "cycle_content"},
    )
    assert second_response.status_code == 200
    second = second_response.json()["data"]
    assert second["segments"]
    assert second["segments"] != first["segments"]

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert current_response.status_code == 200
    assert current_response.json()["data"]["current_stop_index"] == 0


@pytest.mark.asyncio
async def test_cycle_content_rotates_segments_without_finishing_stop(
    client: AsyncClient, db_session, monkeypatch
) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    async def fake_new_session():
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={"user_id": "user-refresh", "title": "Refresh trip", "preferences": {"preferred_poi_count": 1}},
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

    await run_guide_generation_job({}, enqueued["job_id"])

    first_response = await client.post(
        f"/api/v1/guide/content/{guide_session_id}",
        json={"action": "cycle_content"},
    )
    assert first_response.status_code == 200
    first = first_response.json()["data"]

    second_response = await client.post(
        f"/api/v1/guide/content/{guide_session_id}",
        json={"action": "cycle_content"},
    )
    assert second_response.status_code == 200
    second = second_response.json()["data"]
    assert second["stop_id"] == first["stop_id"]
    assert second["segments"] != first["segments"]


@pytest.mark.asyncio
async def test_finished_session_cannot_cycle_guide_content(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={"user_id": "user-finished", "title": "Finished trip", "preferences": {"preferred_poi_count": 1}},
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
    await client.post(f"/api/v1/session/guide/{guide_session_id}/finish")

    response = await client.post(
        f"/api/v1/guide/content/{guide_session_id}",
        json={"action": "cycle_content"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cycle_content_degrades_safely_when_tts_provider_fails(
    client: AsyncClient, db_session, monkeypatch, tmp_path: Path
) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    class FakeSettings:
        tts_api_key = "test-key"
        tts_provider = "dashscope"
        tts_base_url = "https://dashscope.aliyuncs.com/api/v1"
        tts_model = "qwen3-tts-flash"
        tts_voice = "Cherry"
        tts_audio_format = "mp3"
        tts_storage_dir = f".generated_tts_test_{tmp_path.name}"

    class FakeDashscopeResponse:
        output = {}

    class FakeMultiModalConversation:
        @staticmethod
        def call(**kwargs):
            return FakeDashscopeResponse()

    class FakeDashscope:
        base_http_api_url = ""
        MultiModalConversation = FakeMultiModalConversation

    async def fake_new_session():
        return db_session

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)
    monkeypatch.setattr("yoyo.modules.guide.tts.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("yoyo.modules.guide.tts.dashscope", FakeDashscope)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={"user_id": "user-cycle-tts", "title": "Cycle trip", "preferences": {"preferred_poi_count": 2}},
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

    await run_guide_generation_job({}, enqueued["job_id"])

    response = await client.post(
        f"/api/v1/guide/content/{guide_session_id}",
        json={"action": "cycle_content"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["segments"]
    assert {item["status"] for item in data["audio_segments"]} == {"unavailable"}
