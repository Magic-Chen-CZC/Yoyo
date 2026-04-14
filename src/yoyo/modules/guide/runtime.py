# runtime.py 负责 guide generation job 在运行期的状态更新。
# 可以把它看成后台任务的状态切换助手。
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.modules.shared.enums import AssetStatus, GuideGenerationJobStatus


async def mark_job_running(session: AsyncSession, job: GuideGenerationJob) -> None:
    job.status = GuideGenerationJobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    await session.commit()


async def mark_job_succeeded(
    session: AsyncSession, job: GuideGenerationJob, result: dict
) -> None:
    job.status = GuideGenerationJobStatus.SUCCEEDED
    job.asset_status = AssetStatus.READY
    job.result_json = result
    job.finished_at = datetime.now(timezone.utc)
    await session.commit()


async def mark_job_failed(
    session: AsyncSession, job: GuideGenerationJob, error_message: str
) -> None:
    job.status = GuideGenerationJobStatus.FAILED
    job.asset_status = AssetStatus.FAILED
    job.error_message = error_message
    job.finished_at = datetime.now(timezone.utc)
    await session.commit()
