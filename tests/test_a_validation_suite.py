from pathlib import Path

import pytest
from httpx import AsyncClient

from yoyo.jobs.tasks.guide_generation import run_guide_generation_job

PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def _patch_planner_job_pool(monkeypatch, enqueued: dict[str, str] | None = None) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            if enqueued is not None:
                enqueued["function_name"] = function_name
                enqueued["job_id"] = job_id
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)


async def _create_itinerary(
    client: AsyncClient,
    *,
    user_id: str,
    title: str,
    preferred_poi_count: int,
) -> dict:
    response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": user_id,
            "title": title,
            "preferences": {"preferred_poi_count": preferred_poi_count},
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


async def _create_guide_session(
    client: AsyncClient,
    itinerary_data: dict,
    *,
    context: dict | None = None,
) -> str:
    response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": context or {},
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


@pytest.mark.asyncio
async def test_a1_replace_stop_creates_new_version_and_lists_prior_versions(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a1-replace",
        title="A1 replace route",
        preferred_poi_count=2,
    )

    response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "replace_stop",
            "target_stop_id": "stop-forbidden-city",
            "replacement_stop_name": "Jingshan Park",
        },
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["version"]["version_no"] == 2
    assert body["current_version_id"] == body["version"]["id"]
    assert [stop["id"] for stop in body["version"]["plan"]["stops"]] == [
        "stop-tiananmen-square",
        "stop-jingshan-park",
    ]

    versions_response = await client.get(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/versions"
    )
    assert versions_response.status_code == 200
    versions = versions_response.json()["data"]
    assert [version["version_no"] for version in versions] == [2, 1]
    assert [version["status"] for version in versions] == ["active", "archived"]


@pytest.mark.asyncio
async def test_a1_invalid_route_edit_returns_400(client: AsyncClient, monkeypatch) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a1-invalid",
        title="A1 invalid route",
        preferred_poi_count=2,
    )

    response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "reorder_stops",
            "ordered_stop_ids": ["stop-tiananmen-square"],
        },
    )
    assert response.status_code == 400
    assert "ordered_stop_ids" in response.json()["detail"]


@pytest.mark.asyncio
async def test_a2_session_current_uses_current_stop_index(client: AsyncClient, monkeypatch) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a2-session-current",
        title="A2 session current",
        preferred_poi_count=3,
    )
    guide_session_id = await _create_guide_session(
        client,
        itinerary_data,
        context={"current_stop_index": 1},
    )

    response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["current_stop_index"] == 1
    assert body["current_stop"]["id"] == "stop-forbidden-city"
    assert body["next_stop"]["id"] == "stop-jingshan-park"
    assert body["has_next_stop"] is True


@pytest.mark.asyncio
async def test_a2_session_remaps_current_stop_after_route_reorder(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a2-remap",
        title="A2 remap",
        preferred_poi_count=3,
    )
    guide_session_id = await _create_guide_session(
        client,
        itinerary_data,
        context={"current_stop_index": 0},
    )

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

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert current_response.status_code == 200
    current = current_response.json()["data"]
    assert current["current_stop_index"] == 2
    assert current["current_stop"]["id"] == "stop-tiananmen-square"
    assert current["has_next_stop"] is False


@pytest.mark.asyncio
async def test_a3_gps_far_position_does_not_trigger_arrival(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a3-far",
        title="A3 far gps",
        preferred_poi_count=2,
    )
    guide_session_id = await _create_guide_session(client, itinerary_data)

    response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9042, "longitude": 116.4074},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["arrived"] is False
    assert body["current_stop_index"] == 0
    assert body["distance_to_current_stop_meters"] > body["arrival_threshold_meters"]

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert current_response.status_code == 200
    assert current_response.json()["data"]["playback_state"] == "not_triggered"


@pytest.mark.asyncio
async def test_a3_gps_arrival_triggers_once_without_advancing_stop_index(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a3-near",
        title="A3 near gps",
        preferred_poi_count=2,
    )
    guide_session_id = await _create_guide_session(client, itinerary_data)

    first_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    assert first_response.status_code == 200
    first_body = first_response.json()["data"]
    assert first_body["arrived"] is True
    assert first_body["distance_to_current_stop_meters"] == 0
    assert first_body["current_stop_index"] == 0

    guide_session_response = await client.get(f"/api/v1/session/guide/{guide_session_id}")
    assert guide_session_response.status_code == 200
    guide_context = guide_session_response.json()["data"]["context"]
    assert guide_context["last_arrived_stop_id"] == "stop-tiananmen-square"
    assert guide_context["playback_state"] == "triggered"

    second_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    assert second_response.status_code == 200
    second_body = second_response.json()["data"]
    assert second_body["arrived"] is True
    assert second_body["current_stop_index"] == 0


@pytest.mark.asyncio
async def test_a4_map_payload_exposes_stable_navigation_fields(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a4-map",
        title="A4 map stable",
        preferred_poi_count=2,
    )
    guide_session_id = await _create_guide_session(client, itinerary_data)

    response = await client.get(f"/api/v1/map/session/{guide_session_id}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert set(body["markers"][0].keys()) == {
        "id",
        "name",
        "category",
        "latitude",
        "longitude",
        "order",
        "is_current",
        "is_next",
        "is_completed",
        "is_editable",
        "short_intro",
        "highlights",
        "visitor_tip",
        "source_type",
        "comment_count",
        "latest_comment_preview",
    }
    assert set(body["polyline"][0].keys()) == {"stop_id", "order", "latitude", "longitude"}
    assert set(body["navigation_summary"].keys()) == {
        "current_stop_index",
        "stop_count",
        "remaining_stop_count",
        "completed_stop_count",
        "editable_from_stop_index",
        "has_next_stop",
    }


@pytest.mark.asyncio
async def test_a4_map_payload_stays_in_sync_with_session_current(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a4-sync",
        title="A4 map sync",
        preferred_poi_count=2,
    )
    guide_session_id = await _create_guide_session(client, itinerary_data)

    await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "play"},
    )
    await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "complete"},
    )

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    map_response = await client.get(f"/api/v1/map/session/{guide_session_id}")
    assert current_response.status_code == 200
    assert map_response.status_code == 200
    current_body = current_response.json()["data"]
    map_body = map_response.json()["data"]
    assert (
        current_body["current_stop_index"]
        == map_body["navigation_summary"]["current_stop_index"]
    )
    assert current_body["current_stop"]["id"] == map_body["current_stop"]["id"]
    assert current_body["next_stop"] is None or (
        current_body["next_stop"]["id"] == map_body["next_stop"]["id"]
    )


@pytest.mark.asyncio
async def test_a5_contract_fields_exist_in_runtime_payloads(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a5-contract-runtime",
        title="A5 runtime contract",
        preferred_poi_count=2,
    )
    guide_session_id = await _create_guide_session(client, itinerary_data)

    stop = itinerary_data["version"]["plan"]["stops"][0]
    assert {
        "id",
        "name",
        "category",
        "latitude",
        "longitude",
        "recommended_duration_minutes",
        "arrival_threshold_meters",
    }.issubset(stop.keys())

    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    map_response = await client.get(f"/api/v1/map/session/{guide_session_id}")
    assert current_response.status_code == 200
    assert map_response.status_code == 200

    current_data = current_response.json()["data"]
    map_data = map_response.json()["data"]
    assert {
        "current_stop_index",
        "has_next_stop",
        "stop_count",
        "plan_summary",
    }.issubset(current_data.keys())
    assert {"markers", "polyline", "navigation_summary"}.issubset(map_data.keys())


def test_a5_contract_docs_match_runtime_field_names() -> None:
    architecture_doc = (PROJECT_ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    contracts_doc = (PROJECT_ROOT / "docs/contracts.md").read_text(encoding="utf-8")

    for required_field in [
        "arrival_threshold_meters",
        "current_stop_index",
        "has_next_stop",
        "navigation_summary",
    ]:
        assert required_field in architecture_doc

    for required_field in [
        "arrival_threshold_meters",
        "current_stop_index",
        "has_next_stop",
    ]:
        assert required_field in contracts_doc


@pytest.mark.asyncio
async def test_a_integration_happy_path_runs_end_to_end(
    client: AsyncClient, db_session, monkeypatch
) -> None:
    enqueued: dict[str, str] = {}
    await _patch_planner_job_pool(monkeypatch, enqueued)

    async def fake_new_session():
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)

    itinerary_data = await _create_itinerary(
        client,
        user_id="a-int-happy",
        title="A integration happy",
        preferred_poi_count=2,
    )
    assert enqueued["function_name"] == "run_guide_generation_job"
    await run_guide_generation_job({}, enqueued["job_id"])

    guide_session_id = await _create_guide_session(client, itinerary_data)

    asset_response = await client.get(f"/api/v1/guide/asset/{guide_session_id}")
    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    map_response = await client.get(f"/api/v1/map/session/{guide_session_id}")
    gps_far_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9042, "longitude": 116.4074},
    )
    gps_near_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    play_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "play"},
    )
    complete_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "complete"},
    )

    assert asset_response.status_code == 200
    asset_data = asset_response.json()["data"]
    assert asset_data["asset_status"] == "ready"
    assert asset_data["summary"] == "Starter Beijing itinerary"
    assert asset_data["result"]["guide_script"]["title"] == "Starter Beijing itinerary"
    assert asset_data["result"]["stops"] == ["Tiananmen Square", "Forbidden City"]

    assert current_response.status_code == 200
    current_data = current_response.json()["data"]
    assert current_data["itinerary_version_id"] == itinerary_data["version"]["id"]
    assert current_data["current_stop"]["id"] == "stop-tiananmen-square"
    assert current_data["next_stop"]["id"] == "stop-forbidden-city"

    assert map_response.status_code == 200
    map_data = map_response.json()["data"]
    assert map_data["current_stop"]["id"] == current_data["current_stop"]["id"]
    assert map_data["next_stop"]["id"] == current_data["next_stop"]["id"]
    assert [point["stop_id"] for point in map_data["polyline"]] == [
        "stop-tiananmen-square",
        "stop-forbidden-city",
    ]

    assert gps_far_response.status_code == 200
    assert gps_far_response.json()["data"]["arrived"] is False
    assert gps_near_response.status_code == 200
    assert gps_near_response.json()["data"]["arrived"] is True
    assert play_response.status_code == 200
    assert play_response.json()["data"]["playback_state"] == "playing"
    assert complete_response.status_code == 200
    assert complete_response.json()["data"]["playback_state"] == "not_triggered"

    current_after_complete = await client.get(f"/api/v1/session/{guide_session_id}/current")
    map_after_complete = await client.get(f"/api/v1/map/session/{guide_session_id}")
    assert current_after_complete.status_code == 200
    assert map_after_complete.status_code == 200
    current_after_complete_data = current_after_complete.json()["data"]
    map_after_complete_data = map_after_complete.json()["data"]
    assert current_after_complete_data["current_stop_index"] == 1
    assert current_after_complete_data["current_stop"]["id"] == "stop-forbidden-city"
    assert current_after_complete_data["completed_stop_count"] == 1
    assert current_after_complete_data["editable_from_stop_index"] == 1
    assert current_after_complete_data["frozen_stop_ids"] == ["stop-tiananmen-square"]
    assert current_after_complete_data["editable_stop_ids"] == ["stop-forbidden-city"]
    assert map_after_complete_data["current_stop"]["id"] == "stop-forbidden-city"
    assert map_after_complete_data["navigation_summary"]["current_stop_index"] == 1
    assert map_after_complete_data["navigation_summary"]["completed_stop_count"] == 1
    assert map_after_complete_data["navigation_summary"]["editable_from_stop_index"] == 1
    assert [marker["id"] for marker in map_after_complete_data["markers"]] == [
        "stop-tiananmen-square",
        "stop-forbidden-city",
    ]
    assert [marker["is_completed"] for marker in map_after_complete_data["markers"]] == [True, False]

    edit_response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "replace_stop",
            "target_stop_id": "stop-forbidden-city",
            "replacement_stop_name": "Jingshan Park",
        },
    )
    assert edit_response.status_code == 200
    edited_data = edit_response.json()["data"]

    versions_after_edit = await client.get(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/versions"
    )
    current_after_edit = await client.get(f"/api/v1/session/{guide_session_id}/current")
    guide_session_after_edit = await client.get(f"/api/v1/session/guide/{guide_session_id}")
    map_after_edit = await client.get(f"/api/v1/map/session/{guide_session_id}")

    assert versions_after_edit.status_code == 200
    assert current_after_edit.status_code == 200
    assert guide_session_after_edit.status_code == 200
    assert map_after_edit.status_code == 200

    versions_after_edit_data = versions_after_edit.json()["data"]
    current_after_edit_data = current_after_edit.json()["data"]
    guide_session_after_edit_data = guide_session_after_edit.json()["data"]
    map_after_edit_data = map_after_edit.json()["data"]

    assert [version["version_no"] for version in versions_after_edit_data] == [2, 1]
    assert [version["status"] for version in versions_after_edit_data] == ["active", "archived"]
    assert current_after_edit_data["itinerary_version_id"] == edited_data["version"]["id"]
    assert current_after_edit_data["current_stop"]["id"] == "stop-jingshan-park"
    assert current_after_edit_data["next_stop"] is None
    assert current_after_edit_data["completed_stop_count"] == 1
    assert current_after_edit_data["editable_from_stop_index"] == 1
    assert current_after_edit_data["frozen_stop_ids"] == ["stop-tiananmen-square"]
    assert current_after_edit_data["editable_stop_ids"] == ["stop-jingshan-park"]
    assert map_after_edit_data["current_stop"]["id"] == "stop-jingshan-park"
    assert map_after_edit_data["next_stop"] is None
    assert map_after_edit_data["navigation_summary"]["current_stop_index"] == 1
    assert map_after_edit_data["navigation_summary"]["completed_stop_count"] == 1
    assert map_after_edit_data["navigation_summary"]["editable_from_stop_index"] == 1
    assert map_after_edit_data["navigation_summary"]["has_next_stop"] is False
    assert [marker["id"] for marker in map_after_edit_data["markers"]] == [
        "stop-tiananmen-square",
        "stop-jingshan-park",
    ]
    assert [marker["is_completed"] for marker in map_after_edit_data["markers"]] == [True, False]
    assert [marker["is_editable"] for marker in map_after_edit_data["markers"]] == [False, True]
    assert [point["stop_id"] for point in map_after_edit_data["polyline"]] == [
        "stop-tiananmen-square",
        "stop-jingshan-park",
    ]

    context_after_edit = guide_session_after_edit_data["context"]
    assert context_after_edit.get("last_arrived_stop_id") is None
    assert context_after_edit.get("last_played_stop_id") is None
    assert "last_played_stop_index" not in context_after_edit
    assert "last_playback_action" not in context_after_edit
    assert "last_playback_updated_at" not in context_after_edit
    assert "stop_segment_cursor_by_stop_id" not in context_after_edit
    assert "played_segment_indices_by_stop_id" not in context_after_edit
    assert "last_refresh_action" not in context_after_edit
    assert "last_refresh_at" not in context_after_edit


@pytest.mark.asyncio
async def test_a_integration_last_stop_completion_keeps_terminal_state(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a-int-terminal",
        title="A integration terminal",
        preferred_poi_count=2,
    )
    guide_session_id = await _create_guide_session(
        client,
        itinerary_data,
        context={"current_stop_index": 1},
    )

    gps_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9163, "longitude": 116.3972},
    )
    complete_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "complete"},
    )
    current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")

    assert gps_response.status_code == 200
    assert gps_response.json()["data"]["arrived"] is True
    assert complete_response.status_code == 200
    assert complete_response.json()["data"]["playback_state"] == "played"
    assert current_response.status_code == 200
    current_data = current_response.json()["data"]
    assert current_data["current_stop_index"] == 2
    assert current_data["playback_state"] == "played"
    assert current_data["completed_stop_count"] == 2
    assert current_data["editable_from_stop_index"] == 2
    assert current_data["current_stop"] is None
    assert current_data["editable_stop_ids"] == []


@pytest.mark.asyncio
async def test_a_integration_invalid_edit_does_not_pollute_previous_state(
    client: AsyncClient, monkeypatch
) -> None:
    await _patch_planner_job_pool(monkeypatch)
    itinerary_data = await _create_itinerary(
        client,
        user_id="a-int-invalid",
        title="A integration invalid edit",
        preferred_poi_count=2,
    )
    guide_session_id = await _create_guide_session(client, itinerary_data)

    before_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert before_response.status_code == 200
    before_data = before_response.json()["data"]

    invalid_edit_response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "shorten_route",
            "target_stop_count": 0,
        },
    )
    assert invalid_edit_response.status_code == 400

    after_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    versions_response = await client.get(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/versions"
    )
    assert after_response.status_code == 200
    assert versions_response.status_code == 200
    after_data = after_response.json()["data"]
    versions = versions_response.json()["data"]
    assert after_data["itinerary_version_id"] == before_data["itinerary_version_id"]
    assert after_data["current_stop_index"] == before_data["current_stop_index"]
    assert len(versions) == 1
