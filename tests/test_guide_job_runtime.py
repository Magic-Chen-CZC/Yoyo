# 这份测试聚焦后台任务 run_guide_generation_job。
# 重点是确认：job 状态会更新、result_json 结构符合预期。
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import Itinerary, ItineraryVersion
from yoyo.jobs.tasks.guide_generation import run_guide_generation_job
from yoyo.modules.shared.enums import AssetStatus, GuideGenerationJobStatus, GuideGenerationJobType, ItineraryStatus, ItineraryVersionStatus


@pytest.mark.asyncio
async def test_run_guide_generation_job_updates_job(db_session: AsyncSession, monkeypatch) -> None:
    itinerary = Itinerary(user_id="runtime-user", city_code="beijing", title="Runtime trip", status=ItineraryStatus.ACTIVE)
    db_session.add(itinerary)
    await db_session.flush()

    version = ItineraryVersion(
        itinerary_id=itinerary.id,
        version_no=1,
        planner_input_json={"preferences": {"preferred_poi_count": 2}},
        plan_json={
            "summary": "Starter Beijing itinerary",
            "stops": [{"name": "Tiananmen Square"}, {"name": "Forbidden City"}],
        },
        status=ItineraryVersionStatus.ACTIVE,
        created_by="test",
    )
    db_session.add(version)
    await db_session.flush()

    itinerary.current_version_id = version.id

    job = GuideGenerationJob(
        itinerary_version_id=version.id,
        job_type=GuideGenerationJobType.GUIDE_BUNDLE,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        payload_json={"itinerary_id": itinerary.id, "itinerary_version_id": version.id},
    )
    db_session.add(job)
    await db_session.commit()

    async def fake_new_session() -> AsyncSession:
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)

    result = await run_guide_generation_job({}, job.id)

    assert result["status"] == "succeeded"

    persisted_job = await db_session.get(GuideGenerationJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == GuideGenerationJobStatus.SUCCEEDED
    assert persisted_job.asset_status == AssetStatus.READY
    assert persisted_job.result_json == {
        "summary": "Starter Beijing itinerary",
        "stop_count": 2,
        "stops": ["Tiananmen Square", "Forbidden City"],
        "guide_script": {
            "title": "Starter Beijing itinerary",
            "intro": "This route starts with Tiananmen Square and includes 2 stop(s).",
        },
        "card": {
            "headline": "Starter Beijing itinerary",
            "highlights": ["Tiananmen Square", "Forbidden City"],
        },
        "audio": {
            "status": "not_generated",
            "url": None,
        },
    }
