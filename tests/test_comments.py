import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stop_comments_create_and_list(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/comments/stops/stop-forbidden-city",
        json={
            "user_id": "guest-comment-1",
            "content": "Great view and clear route pacing.",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["stop_id"] == "stop-forbidden-city"
    assert created["user_id"] == "guest-comment-1"

    list_response = await client.get("/api/v1/comments/stops/stop-forbidden-city")
    assert list_response.status_code == 200
    comments = list_response.json()["data"]
    assert len(comments) == 1
    assert comments[0]["content"] == "Great view and clear route pacing."


@pytest.mark.asyncio
async def test_map_payload_includes_comment_summary(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-map-comments",
            "title": "Map comment trip",
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

    await client.post(
        "/api/v1/comments/stops/stop-tiananmen-square",
        json={
            "user_id": "guest-comment-2",
            "content": "Open square, easy to orient yourself.",
        },
    )

    map_response = await client.get(f"/api/v1/map/session/{guide_session_id}")
    assert map_response.status_code == 200
    markers = map_response.json()["data"]["markers"]
    tiananmen = next(item for item in markers if item["id"] == "stop-tiananmen-square")
    assert tiananmen["comment_count"] == 1
    assert tiananmen["latest_comment_preview"] == "Open square, easy to orient yourself."
    assert tiananmen["short_intro"]
