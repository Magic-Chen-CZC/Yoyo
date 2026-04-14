# test_qa.py 是 QA 模块最重要的行为测试之一。
# 它覆盖了 QA 支持的几条主要路径，适合当成“QA 能做什么”的说明书来看。
from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_qa_out_of_scope(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Write me a sorting algorithm", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is False
    assert body["data"]["intent"] == "out_of_scope"


@pytest.mark.asyncio
async def test_qa_translation_intent(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Please translate this Beijing phrase", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is True
    assert body["data"]["intent"] == "translation"
    assert "translate_text" in body["data"]["used_skills"]
    assert "guided mode" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_qa_live_info_includes_sources(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "What are today's opening hours in Beijing?", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "live_info"
    assert len(body["data"]["metadata"]["sources"]) >= 1
    assert "updated_at" in body["data"]["metadata"]
    assert "confidence" in body["data"]["metadata"]


@pytest.mark.asyncio
async def test_session_aware_trip_assistant_answer(client: AsyncClient, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-qa",
            "title": "QA trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "en"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my next route stop in Beijing itinerary?",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["supported"] is True
    assert body["data"]["intent"] == "trip_assistant"
    assert "Tiananmen Square" in body["data"]["answer"]
    assert "Forbidden City" in body["data"]["answer"]
    assert body["data"]["metadata"]["context"]["session_context"]["stop_count"] == 2


@pytest.mark.asyncio
async def test_session_aware_attraction_explain_returns_retrieval(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-attraction",
            "title": "Attraction QA trip",
            "preferences": {"preferred_poi_count": 1},
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

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "Tell me about this Beijing attraction",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert "Tiananmen Square" in body["data"]["answer"]
    assert "Historical note" in body["data"]["answer"]
    assert "Visitor tip" in body["data"]["answer"]
    assert body["data"]["metadata"]["retrieval"]["name"] == "Tiananmen Square"
