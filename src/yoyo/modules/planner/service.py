from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import Itinerary, ItineraryVersion
from yoyo.jobs.queue import get_job_pool
from yoyo.modules.planner.rules import build_default_plan
from yoyo.modules.planner.schemas import CreateItineraryRequest, ItineraryRead, ItineraryVersionRead
from yoyo.modules.shared.enums import (
    AssetStatus,
    GuideGenerationJobStatus,
    GuideGenerationJobType,
    ItineraryStatus,
    ItineraryVersionStatus,
)


async def create_itinerary(session: AsyncSession, payload: CreateItineraryRequest) -> ItineraryRead:
    planner_input = {
        "questionnaire_submission_id": payload.questionnaire_submission_id,
        "preferences": payload.preferences,
    }
    plan = build_default_plan(payload.preferences)

    itinerary = Itinerary(
        user_id=payload.user_id,
        city_code=payload.city_code,
        title=payload.title,
        status=ItineraryStatus.ACTIVE,
    )
    session.add(itinerary)
    await session.flush()

    version = ItineraryVersion(
        itinerary_id=itinerary.id,
        version_no=1,
        planner_input_json=planner_input,
        plan_json=plan,
        status=ItineraryVersionStatus.ACTIVE,
        created_by="planner_v0",
    )
    session.add(version)
    await session.flush()

    itinerary.current_version_id = version.id

    job = GuideGenerationJob(
        itinerary_version_id=version.id,
        job_type=GuideGenerationJobType.GUIDE_BUNDLE,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        payload_json={"itinerary_id": itinerary.id, "itinerary_version_id": version.id},
    )
    session.add(job)
    await session.commit()
    await session.refresh(itinerary)
    await session.refresh(version)
    await session.refresh(job)

    redis = await get_job_pool()
    await redis.enqueue_job("run_guide_generation_job", job.id)

    return _serialize_itinerary(itinerary, version)


async def get_itinerary(session: AsyncSession, itinerary_id: str) -> ItineraryRead | None:
    itinerary = await session.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.current_version_id is None:
        return None

    version = await session.get(ItineraryVersion, itinerary.current_version_id)
    if version is None:
        return None

    return _serialize_itinerary(itinerary, version)


def _serialize_itinerary(itinerary: Itinerary, version: ItineraryVersion) -> ItineraryRead:
    return ItineraryRead(
        id=itinerary.id,
        user_id=itinerary.user_id,
        city_code=itinerary.city_code,
        title=itinerary.title,
        status=itinerary.status.value,
        current_version_id=itinerary.current_version_id,
        version=ItineraryVersionRead(
            id=version.id,
            version_no=version.version_no,
            status=version.status.value,
            planner_input=version.planner_input_json,
            plan=version.plan_json,
        ),
    )
