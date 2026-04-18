# test_api_flow.py 更像一份“接口层使用说明”。
# 它通过真实 API 调用来验证核心流程能否串起来。
import pytest


@pytest.mark.asyncio
async def test_questionnaire_submission_flow(client) -> None:
    response = await client.post(
        "/api/v1/questionnaire/submissions",
        json={
            "user_id": "user-1",
            "role_choice": "balanced_storyteller",
            "answers": {
                "preferred_language": "en",
                "interests": ["history", "culture"],
                "travel_style": "balanced",
                "walking_preference": "moderate",
                "audience_type": "general",
                "answer_length_preference": "medium",
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    assert body["message"] == "created"
    assert body["data"]["user_id"] == "user-1"
    assert body["data"]["payload"]["flow_version"] == "v1"
    assert body["data"]["payload"]["role_choice"] == "balanced_storyteller"
    assert body["data"]["payload"]["answers"]["guide_role"] == "balanced_storyteller"


@pytest.mark.asyncio
async def test_create_itinerary_flow(client, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-1",
            "title": "Starter trip",
            "preferences": {"travel_pace": "fast", "preferred_poi_count": 2},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "active"
    assert body["data"]["version"]["version_no"] == 1
    assert len(body["data"]["version"]["plan"]["stops"]) == 2
    first_stop = body["data"]["version"]["plan"]["stops"][0]
    assert first_stop["id"] == "stop-tiananmen-square"
    assert first_stop["category"] == "landmark"
    assert first_stop["latitude"] == 39.905
    assert first_stop["longitude"] == 116.3976
    assert first_stop["recommended_duration_minutes"] == 45
    assert enqueued["function_name"] == "run_guide_generation_job"

    itinerary_id = body["data"]["id"]
    get_response = await client.get(f"/api/v1/planning/itineraries/{itinerary_id}")
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["data"]["id"] == itinerary_id


@pytest.mark.asyncio
async def test_create_and_get_guide_job(client, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.guide.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-2",
            "title": "Guide job trip",
            "preferences": {"preferred_poi_count": 1},
        },
    )
    itinerary_version_id = itinerary_response.json()["data"]["version"]["id"]

    response = await client.post(
        "/api/v1/guide/jobs",
        json={
            "itinerary_version_id": itinerary_version_id,
            "payload": {"requested_by": "test"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["status"] == "queued"
    assert body["data"]["asset_status"] == "pending"
    assert enqueued["function_name"] == "run_guide_generation_job"

    job_id = body["data"]["id"]
    get_response = await client.get(f"/api/v1/guide/jobs/{job_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == job_id
