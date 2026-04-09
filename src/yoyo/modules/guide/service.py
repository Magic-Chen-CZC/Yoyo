from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.jobs.queue import get_job_pool
from yoyo.modules.guide.schemas import CreateGuideGenerationJobRequest, GuideGenerationJobRead
from yoyo.modules.shared.enums import AssetStatus, GuideGenerationJobStatus, GuideGenerationJobType


async def create_guide_generation_job(
    session: AsyncSession, payload: CreateGuideGenerationJobRequest
) -> GuideGenerationJobRead:
    job = GuideGenerationJob(
        itinerary_version_id=payload.itinerary_version_id,
        job_type=GuideGenerationJobType.GUIDE_BUNDLE,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        payload_json=payload.payload,
        queued_at=datetime.now(timezone.utc),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    redis = await get_job_pool()
    await redis.enqueue_job("run_guide_generation_job", job.id)

    return _serialize_job(job)


async def get_guide_generation_job(
    session: AsyncSession, guide_generation_job_id: str
) -> GuideGenerationJobRead | None:
    job = await session.get(GuideGenerationJob, guide_generation_job_id)
    if job is None:
        return None

    return _serialize_job(job)


def _serialize_job(job: GuideGenerationJob) -> GuideGenerationJobRead:
    return GuideGenerationJobRead(
        id=job.id,
        itinerary_version_id=job.itinerary_version_id,
        job_type=job.job_type.value,
        status=job.status.value,
        asset_status=job.asset_status.value,
        payload=job.payload_json,
        result=job.result_json,
        error_code=job.error_code,
        error_message=job.error_message,
    )
