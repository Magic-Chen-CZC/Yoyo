import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_replace_stop_creates_new_version_updates_active_session_and_lists_versions(
    client: AsyncClient, monkeypatch
) -> None:
    enqueued_job_ids: list[str] = []

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            assert function_name == "run_guide_generation_job"
            enqueued_job_ids.append(job_id)

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-edit",
            "title": "Editable trip",
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
                "last_arrived_stop_id": "stop-forbidden-city",
            },
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    playback_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "play"},
    )
    assert playback_response.status_code == 200
    assert playback_response.json()["data"]["playback_state"] == "playing"

    edit_response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "replace_stop",
            "target_stop_id": "stop-forbidden-city",
            "replacement_stop_name": "Jingshan Park",
        },
    )
    assert edit_response.status_code == 200
    edit_body = edit_response.json()
    assert edit_body["data"]["version"]["version_no"] == 2
    assert edit_body["data"]["version"]["plan"]["stops"][1]["id"] == "stop-jingshan-park"
    assert len(enqueued_job_ids) == 2

    session_current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert session_current_response.status_code == 200
    session_current = session_current_response.json()["data"]
    assert session_current["itinerary_version_id"] == edit_body["data"]["version"]["id"]
    assert session_current["current_stop_index"] == 1
    assert session_current["current_stop"]["id"] == "stop-jingshan-park"
    assert session_current["playback_state"] == "not_triggered"

    guide_session_state_response = await client.get(f"/api/v1/session/guide/{guide_session_id}")
    assert guide_session_state_response.status_code == 200
    guide_session_state = guide_session_state_response.json()["data"]["context"]
    assert guide_session_state["last_arrived_stop_id"] is None

    versions_response = await client.get(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/versions"
    )
    assert versions_response.status_code == 200
    versions = versions_response.json()["data"]
    assert [version["version_no"] for version in versions] == [2, 1]
    assert [version["status"] for version in versions] == ["active", "archived"]


@pytest.mark.asyncio
async def test_remove_stop_clamps_current_stop_index_on_active_session(
    client: AsyncClient, monkeypatch
) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-remove",
            "title": "Removal trip",
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
                "last_arrived_stop_id": "stop-forbidden-city",
            },
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    edit_response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "remove_stop",
            "target_stop_name": "Forbidden City",
        },
    )
    assert edit_response.status_code == 200
    edit_body = edit_response.json()["data"]
    assert [stop["id"] for stop in edit_body["version"]["plan"]["stops"]] == [
        "stop-tiananmen-square"
    ]

    session_current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert session_current_response.status_code == 200
    session_current = session_current_response.json()["data"]
    assert session_current["current_stop_index"] == 0
    assert session_current["current_stop"]["id"] == "stop-tiananmen-square"
    assert session_current["has_next_stop"] is False

    guide_session_state_response = await client.get(f"/api/v1/session/guide/{guide_session_id}")
    assert guide_session_state_response.status_code == 200
    guide_session_state = guide_session_state_response.json()["data"]["context"]
    assert guide_session_state["last_arrived_stop_id"] is None


@pytest.mark.asyncio
async def test_reorder_stops_preserves_current_stop_by_id(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-reorder",
            "title": "Reorder trip",
            "preferences": {"preferred_poi_count": 3},
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
            },
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    edit_response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "reorder_stops",
            "ordered_stop_ids": [
                "stop-jingshan-park",
                "stop-forbidden-city",
                "stop-tiananmen-square",
            ],
        },
    )
    assert edit_response.status_code == 200

    session_current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert session_current_response.status_code == 200
    session_current = session_current_response.json()["data"]
    assert session_current["current_stop_index"] == 2
    assert session_current["current_stop"]["id"] == "stop-tiananmen-square"
    assert session_current["has_next_stop"] is False


@pytest.mark.asyncio
async def test_shorten_route_trims_tail_to_target_stop_count(
    client: AsyncClient, monkeypatch
) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-shorten",
            "title": "Shorten trip",
            "preferences": {"preferred_poi_count": 3},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    edit_response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "shorten_route",
            "target_stop_count": 1,
        },
    )
    assert edit_response.status_code == 200
    stops = edit_response.json()["data"]["version"]["plan"]["stops"]
    assert len(stops) == 1
    assert stops[0]["id"] == "stop-tiananmen-square"


@pytest.mark.asyncio
async def test_route_edit_validations_return_400(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    duplicate_itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-invalid-duplicate",
            "title": "Invalid duplicate trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    duplicate_itinerary_id = duplicate_itinerary_response.json()["data"]["id"]

    duplicate_replace_response = await client.post(
        f"/api/v1/planning/itineraries/{duplicate_itinerary_id}/edits",
        json={
            "operation": "replace_stop",
            "target_stop_name": "Forbidden City",
            "replacement_stop_name": "Tiananmen Square",
        },
    )
    assert duplicate_replace_response.status_code == 400

    single_stop_itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-invalid-remove",
            "title": "Invalid remove trip",
            "preferences": {"preferred_poi_count": 1},
        },
    )
    single_stop_itinerary_id = single_stop_itinerary_response.json()["data"]["id"]

    remove_last_stop_response = await client.post(
        f"/api/v1/planning/itineraries/{single_stop_itinerary_id}/edits",
        json={
            "operation": "remove_stop",
            "target_stop_id": "stop-tiananmen-square",
        },
    )
    assert remove_last_stop_response.status_code == 400

    reorder_itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-invalid-reorder",
            "title": "Invalid reorder trip",
            "preferences": {"preferred_poi_count": 3},
        },
    )
    reorder_itinerary_id = reorder_itinerary_response.json()["data"]["id"]

    invalid_reorder_response = await client.post(
        f"/api/v1/planning/itineraries/{reorder_itinerary_id}/edits",
        json={
            "operation": "reorder_stops",
            "ordered_stop_ids": [
                "stop-tiananmen-square",
                "stop-forbidden-city",
            ],
        },
    )
    assert invalid_reorder_response.status_code == 400

    shorten_itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-invalid-shorten",
            "title": "Invalid shorten trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    shorten_itinerary_id = shorten_itinerary_response.json()["data"]["id"]

    invalid_shorten_response = await client.post(
        f"/api/v1/planning/itineraries/{shorten_itinerary_id}/edits",
        json={
            "operation": "shorten_route",
            "target_stop_count": 0,
        },
    )
    assert invalid_shorten_response.status_code == 400
