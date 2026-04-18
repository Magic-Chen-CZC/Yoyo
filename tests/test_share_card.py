from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import Itinerary, ItineraryVersion
from yoyo.db.models.session import GuideSession
from yoyo.modules.shared.enums import (
    AssetStatus,
    GuideGenerationJobStatus,
    GuideGenerationJobType,
    GuidePlaybackState,
    GuideSessionStatus,
    ItineraryStatus,
    ItineraryVersionStatus,
)


async def _create_finished_session(db_session: AsyncSession) -> tuple[str, str]:
    itinerary = Itinerary(
        user_id="user-share",
        city_code="beijing",
        title="Shareable Beijing Trip",
        status=ItineraryStatus.COMPLETED,
    )
    db_session.add(itinerary)
    await db_session.flush()

    version = ItineraryVersion(
        itinerary_id=itinerary.id,
        version_no=1,
        planner_input_json={"preferences": {"preferred_poi_count": 2}},
        plan_json={
            "summary": "Shareable Beijing Trip",
            "polyline": [
                {"stop_id": "stop-1", "order": 0, "latitude": 39.905, "longitude": 116.3976},
                {"stop_id": "stop-2", "order": 1, "latitude": 39.9163, "longitude": 116.3972},
            ],
            "stops": [
                {"id": "stop-tiananmen-square", "name": "Tiananmen Square", "latitude": 39.905, "longitude": 116.3976},
                {"id": "stop-forbidden-city", "name": "Forbidden City", "latitude": 39.9163, "longitude": 116.3972},
            ],
        },
        status=ItineraryVersionStatus.ACTIVE,
        created_by="test",
    )
    db_session.add(version)
    await db_session.flush()
    itinerary.current_version_id = version.id

    session = GuideSession(
        itinerary_id=itinerary.id,
        itinerary_version_id=version.id,
        status=GuideSessionStatus.FINISHED,
        playback_state=GuidePlaybackState.PLAYED,
        context_json={"trip_state": "finished", "trip_finished_at": "2026-04-15T10:00:00+00:00"},
    )
    db_session.add(session)
    await db_session.commit()
    return session.id, version.id


async def _create_ready_guide_job(db_session: AsyncSession, itinerary_version_id: str, summary: str) -> None:
    now = datetime.now(timezone.utc)
    db_session.add(
        GuideGenerationJob(
            itinerary_version_id=itinerary_version_id,
            job_type=GuideGenerationJobType.GUIDE_BUNDLE,
            status=GuideGenerationJobStatus.SUCCEEDED,
            asset_status=AssetStatus.READY,
            payload_json={"requested_by": "test"},
            result_json={
                "summary": summary,
                "stop_count": 2,
                "stops": ["Tiananmen Square", "Forbidden City"],
                "card": {
                    "headline": "A memorable Beijing walk",
                    "highlights": ["Imperial history", "Ceremonial square"],
                    "route_style": "balanced",
                    "guide_style": "guardian",
                    "practical_tips": ["Start early", "Wear comfortable shoes"],
                },
            },
            created_at=now - timedelta(minutes=2),
            finished_at=now - timedelta(minutes=1),
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_share_card_returns_finished_session_payload(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    guide_session_id, itinerary_version_id = await _create_finished_session(db_session)
    await _create_ready_guide_job(db_session, itinerary_version_id, "Shareable Beijing Trip")

    response = await client.get(f"/api/v1/share-card/session/{guide_session_id}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["is_shareable"] is True
    assert body["status"] == "finished"
    assert body["headline"] == "A memorable Beijing walk"
    assert body["trip_summary"]["stop_count"] == 2
    assert len(body["map_preview"]["polyline"]) == 2


@pytest.mark.asyncio
async def test_share_card_falls_back_without_ready_guide_asset(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    guide_session_id, _ = await _create_finished_session(db_session)

    response = await client.get(f"/api/v1/share-card/session/{guide_session_id}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["is_shareable"] is True
    assert body["headline"] == "Shareable Beijing Trip"
    assert body["highlights"] == ["Tiananmen Square", "Forbidden City"]


@pytest.mark.asyncio
async def test_share_card_collects_comment_summary(client: AsyncClient, db_session: AsyncSession) -> None:
    guide_session_id, _ = await _create_finished_session(db_session)

    await client.post(
        "/api/v1/comments/stops/stop-forbidden-city",
        json={"user_id": "guest-1", "content": "Loved the courtyard atmosphere."},
    )
    await client.post(
        "/api/v1/comments/stops/stop-forbidden-city",
        json={"user_id": "guest-2", "content": "Great final stop for sharing photos."},
    )

    response = await client.get(f"/api/v1/share-card/session/{guide_session_id}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["social_summary"]["comment_count_total"] == 2
    assert body["social_summary"]["top_commented_stop_name"] == "Forbidden City"
    assert body["social_summary"]["featured_comment_preview"]


@pytest.mark.asyncio
async def test_share_card_is_not_shareable_before_finish(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={"user_id": "user-active", "title": "Active trip", "preferences": {"preferred_poi_count": 2}},
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

    response = await client.get(f"/api/v1/share-card/session/{guide_session_id}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["is_shareable"] is False
    assert body["status"] == "pending"
