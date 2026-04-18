# 这份测试最适合用来理解 Guide 的端到端流程：
# itinerary -> guide session -> guide asset -> playback state。
import pytest
from httpx import AsyncClient

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

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"intro":"Tiananmen Square opens this route with a clear historical frame.","outro":"This finishes the route with a compact takeaway.","card_headline":"Historic Beijing Walk","card_highlights":["large ceremonial square","imperial architecture"],"card_practical_tips":["Start early"],"stop_scripts":[{"stop_name":"Tiananmen Square","narration":"Tiananmen Square is the ceremonial opening of the route.","why_it_matters":"It anchors the political symbolism of modern Beijing.","visitor_tip":"Pause for the broad north-south axis."},{"stop_name":"Forbidden City","narration":"The Forbidden City expands the imperial story.","why_it_matters":"It shows how imperial power was spatially organized.","visitor_tip":"Budget extra time for the main halls."}]}'
            self.provider = "openrouter"
            self.model = "google/gemini-2.5-flash-lite"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    async def fake_new_session():
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)
    monkeypatch.setattr("yoyo.modules.guide.generator.get_llm_runtime", lambda: FakeRuntime())

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
    assert len(asset_body["data"]["result"]["card"]["highlights"]) == 2
    assert "large ceremonial square" in asset_body["data"]["result"]["card"]["highlights"]
    assert "imperial architecture" in asset_body["data"]["result"]["card"]["highlights"]
    assert asset_body["data"]["result"]["audio"]["status"] in {"unavailable", "pending"}
    assert asset_body["data"]["result"]["audio"]["voice"] == "Cherry"

    gps_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    assert gps_response.status_code == 200
    assert gps_response.json()["data"]["arrived"] is True

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
    assert complete_response.json()["data"]["playback_state"] == "not_triggered"

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert current_response.status_code == 200
    current_body = current_response.json()
    assert current_body["data"]["playback_state"] == "not_triggered"
    assert current_body["data"]["current_stop_index"] == 1
    assert current_body["data"]["current_stop"]["id"] == "stop-forbidden-city"
    assert current_body["data"]["completed_stop_count"] == 1
    assert current_body["data"]["frozen_stop_ids"] == ["stop-tiananmen-square"]
    assert current_body["data"]["editable_stop_ids"] == ["stop-forbidden-city"]


@pytest.mark.asyncio
async def test_last_stop_completion_keeps_terminal_playback_state(
    client: AsyncClient, db_session, monkeypatch
) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"intro":"Tiananmen Square opens this route with a clear historical frame.","outro":"This finishes the route with a compact takeaway.","card_headline":"Historic Beijing Walk","card_highlights":["large ceremonial square","imperial architecture"],"card_practical_tips":["Start early"],"stop_scripts":[{"stop_name":"Tiananmen Square","narration":"Tiananmen Square is the ceremonial opening of the route.","why_it_matters":"It anchors the political symbolism of modern Beijing.","visitor_tip":"Pause for the broad north-south axis."},{"stop_name":"Forbidden City","narration":"The Forbidden City expands the imperial story.","why_it_matters":"It shows how imperial power was spatially organized.","visitor_tip":"Budget extra time for the main halls."}]}'
            self.provider = "openrouter"
            self.model = "google/gemini-2.5-flash-lite"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    async def fake_new_session():
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)
    monkeypatch.setattr("yoyo.modules.guide.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-last-stop",
            "title": "Last stop trip",
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
                "current_stop_index": 1,
            },
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    job_id = enqueued["job_id"]
    await run_guide_generation_job({}, job_id)

    gps_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9163, "longitude": 116.3972},
    )
    assert gps_response.status_code == 200
    assert gps_response.json()["data"]["arrived"] is True

    complete_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "complete"},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["data"]["playback_state"] == "played"

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert current_response.status_code == 200
    current_body = current_response.json()["data"]
    assert current_body["current_stop_index"] == 2
    assert current_body["playback_state"] == "played"
    assert current_body["completed_stop_count"] == 2
    assert current_body["editable_from_stop_index"] == 2
    assert current_body["current_stop"] is None
    assert current_body["next_stop"] is None
    assert current_body["frozen_stop_ids"] == [
        "stop-tiananmen-square",
        "stop-forbidden-city",
    ]
    assert current_body["editable_stop_ids"] == []
