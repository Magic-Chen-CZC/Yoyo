# 这份测试专门验证：当前真正生效的 guide asset 应该如何选择。
# 如果你想理解“为什么系统返回的是这个导览结果”，这份测试很值得看。
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
import pytest
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


async def _create_guide_session(db_session: AsyncSession) -> tuple[str, str]:
    itinerary = Itinerary(
        user_id="user-latest",
        city_code="beijing",
        title="Latest guide asset trip",
        status=ItineraryStatus.ACTIVE,
    )
    db_session.add(itinerary)
    await db_session.flush()

    version = ItineraryVersion(
        itinerary_id=itinerary.id,
        version_no=1,
        planner_input_json={"preferences": {"preferred_poi_count": 2}},
        plan_json={
            "summary": "Starter Beijing itinerary",
            "stops": [
                {"id": "stop-1", "name": "Tiananmen Square"},
                {"id": "stop-2", "name": "Forbidden City"},
            ],
        },
        status=ItineraryVersionStatus.ACTIVE,
        created_by="test",
    )
    db_session.add(version)
    await db_session.flush()

    itinerary.current_version_id = version.id

    guide_session = GuideSession(
        itinerary_id=itinerary.id,
        itinerary_version_id=version.id,
        status=GuideSessionStatus.ACTIVE,
        playback_state=GuidePlaybackState.NOT_TRIGGERED,
        context_json={},
    )
    db_session.add(guide_session)
    await db_session.commit()

    return guide_session.id, version.id


async def _create_guide_job(
    db_session: AsyncSession,
    itinerary_version_id: str,
    *,
    status: GuideGenerationJobStatus,
    asset_status: AssetStatus,
    summary: str | None,
    created_at: datetime,
    finished_at: datetime | None,
) -> None:
    result_json = None
    if summary is not None:
        result_json = {
            "summary": summary,
            "stop_count": 2,
            "stops": ["Tiananmen Square", "Forbidden City"],
            "guide_script": {"title": summary, "intro": f"{summary} intro"},
            "card": {"headline": summary, "highlights": ["Tiananmen Square", "Forbidden City"]},
            "audio": {"status": "not_generated", "url": None},
        }

    db_session.add(
        GuideGenerationJob(
            itinerary_version_id=itinerary_version_id,
            job_type=GuideGenerationJobType.GUIDE_BUNDLE,
            status=status,
            asset_status=asset_status,
            payload_json={"requested_by": "test"},
            result_json=result_json,
            created_at=created_at,
            finished_at=finished_at,
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_active_guide_asset_uses_latest_ready_successful_job(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    guide_session_id, itinerary_version_id = await _create_guide_session(db_session)
    now = datetime.now(timezone.utc)

    await _create_guide_job(
        db_session,
        itinerary_version_id,
        status=GuideGenerationJobStatus.SUCCEEDED,
        asset_status=AssetStatus.READY,
        summary="Older guide asset",
        created_at=now - timedelta(minutes=10),
        finished_at=now - timedelta(minutes=9),
    )
    await _create_guide_job(
        db_session,
        itinerary_version_id,
        status=GuideGenerationJobStatus.SUCCEEDED,
        asset_status=AssetStatus.READY,
        summary="Latest guide asset",
        created_at=now - timedelta(minutes=5),
        finished_at=now - timedelta(minutes=1),
    )
    await _create_guide_job(
        db_session,
        itinerary_version_id,
        status=GuideGenerationJobStatus.FAILED,
        asset_status=AssetStatus.FAILED,
        summary=None,
        created_at=now,
        finished_at=now,
    )

    asset_response = await client.get(f"/api/v1/guide/asset/{guide_session_id}")

    assert asset_response.status_code == 200
    body = asset_response.json()
    assert body["data"]["asset_status"] == "ready"
    assert body["data"]["summary"] == "Latest guide asset"
    assert body["data"]["result"]["card"]["headline"] == "Latest guide asset"


@pytest.mark.asyncio
async def test_active_guide_asset_ignores_newer_pending_job(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    guide_session_id, itinerary_version_id = await _create_guide_session(db_session)
    now = datetime.now(timezone.utc)

    await _create_guide_job(
        db_session,
        itinerary_version_id,
        status=GuideGenerationJobStatus.SUCCEEDED,
        asset_status=AssetStatus.READY,
        summary="Stable guide asset",
        created_at=now - timedelta(minutes=6),
        finished_at=now - timedelta(minutes=5),
    )
    await _create_guide_job(
        db_session,
        itinerary_version_id,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        summary=None,
        created_at=now,
        finished_at=None,
    )

    asset_response = await client.get(f"/api/v1/guide/asset/{guide_session_id}")

    assert asset_response.status_code == 200
    body = asset_response.json()
    assert body["data"]["asset_status"] == "ready"
    assert body["data"]["summary"] == "Stable guide asset"


@pytest.mark.asyncio
async def test_active_guide_asset_returns_missing_without_ready_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    guide_session_id, itinerary_version_id = await _create_guide_session(db_session)
    now = datetime.now(timezone.utc)

    await _create_guide_job(
        db_session,
        itinerary_version_id,
        status=GuideGenerationJobStatus.FAILED,
        asset_status=AssetStatus.FAILED,
        summary=None,
        created_at=now - timedelta(minutes=2),
        finished_at=now - timedelta(minutes=1),
    )
    await _create_guide_job(
        db_session,
        itinerary_version_id,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        summary=None,
        created_at=now,
        finished_at=None,
    )

    asset_response = await client.get(f"/api/v1/guide/asset/{guide_session_id}")

    assert asset_response.status_code == 200
    body = asset_response.json()
    assert body["data"]["asset_status"] == "missing"
    assert body["data"]["summary"] is None
    assert body["data"]["result"] is None
