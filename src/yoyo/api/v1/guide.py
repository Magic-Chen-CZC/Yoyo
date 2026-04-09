from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.guide.asset_service import get_active_guide_asset, update_playback_state
from yoyo.modules.guide.schemas import CreateGuideGenerationJobRequest, GuidePlaybackUpdateRequest
from yoyo.modules.guide.service import create_guide_generation_job, get_guide_generation_job

router = APIRouter(prefix="/guide")


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_guide_job_endpoint(
    payload: CreateGuideGenerationJobRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    job = await create_guide_generation_job(session, payload)
    return success_response(job.model_dump(), message="created")


@router.get("/jobs/{guide_generation_job_id}")
async def get_guide_job_endpoint(
    guide_generation_job_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    job = await get_guide_generation_job(session, guide_generation_job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guide job not found")

    return success_response(job.model_dump())


@router.get("/asset/{guide_session_id}")
async def get_active_guide_asset_endpoint(
    guide_session_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    asset = await get_active_guide_asset(session, guide_session_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guide session not found")

    return success_response(asset.model_dump())


@router.post("/playback/{guide_session_id}")
async def update_playback_state_endpoint(
    guide_session_id: str,
    payload: GuidePlaybackUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    playback = await update_playback_state(session, guide_session_id, payload.action)
    if playback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guide session not found")

    return success_response(playback.model_dump())
