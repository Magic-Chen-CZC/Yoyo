import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_route_templates(client: AsyncClient) -> None:
    response = await client.get("/api/v1/planning/templates")
    assert response.status_code == 200
    templates = response.json()["data"]
    assert len(templates) >= 3
    assert any(item["id"] == "classic-central-beijing" for item in templates)


@pytest.mark.asyncio
async def test_create_route_recommendations(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/planning/recommendations",
        json={
            "preferences": {
                "preferred_tags": ["history", "architecture"],
                "selected_poi_ids": ["stop-forbidden-city", "stop-jingshan-park"],
            }
        },
    )
    assert response.status_code == 200
    recommendations = response.json()["data"]
    assert 1 <= len(recommendations) <= 3
    assert all(item["entry_type"] == "ai_recommendation" for item in recommendations)


@pytest.mark.asyncio
async def test_create_itinerary_from_template_entry(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "guest-template",
            "entry_type": "template",
            "template_id": "classic-central-beijing",
            "title": "Template trip",
            "preferences": {},
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["version"]["plan"]["entry_type"] == "template"
    assert data["version"]["plan"]["template_id"] == "classic-central-beijing"
    assert len(data["version"]["plan"]["stops"]) == 3


@pytest.mark.asyncio
async def test_create_itinerary_from_manual_poi_entry(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "guest-manual",
            "entry_type": "manual_poi",
            "title": "Manual trip",
            "selected_poi_ids": ["stop-jingshan-park", "stop-tiananmen-square"],
            "preferences": {"travel_pace": "relaxed"},
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["version"]["plan"]["entry_type"] == "manual_poi"
    assert [stop["id"] for stop in data["version"]["plan"]["stops"]] == [
        "stop-tiananmen-square",
        "stop-jingshan-park",
    ]
    assert data["version"]["plan"]["route_meta"]["degraded"] is True
    assert len(data["version"]["plan"]["polyline"]) == 2


@pytest.mark.asyncio
async def test_create_itinerary_from_ai_recommendation_entry(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "guest-ai",
            "entry_type": "ai_recommendation_selected",
            "title": "AI trip",
            "template_id": "relaxed-view-route",
            "preferences": {},
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["version"]["plan"]["entry_type"] == "ai_recommendation_selected"
    assert data["version"]["plan"]["route_meta"]["waypoint_order_source"] == "ai_recommendation"
    assert data["version"]["plan"]["route_meta"]["degraded"] is True
    assert len(data["version"]["plan"]["polyline"]) >= 2
