from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.session.schemas import CreateGuideSessionRequest
from yoyo.modules.session.service import create_guide_session, get_guide_session, get_guide_session_current

router = APIRouter(prefix="/session")


@router.post("/guide", status_code=status.HTTP_201_CREATED)
async def create_guide_session_endpoint(
    payload: CreateGuideSessionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    guide_session = await create_guide_session(session, payload)
    return success_response(guide_session.model_dump(), message="created")


@router.get("/guide/{guide_session_id}")
async def get_guide_session_endpoint(
    guide_session_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    guide_session = await get_guide_session(session, guide_session_id)
    if guide_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guide session not found")

    return success_response(guide_session.model_dump())


@router.get("/{guide_session_id}/current")
async def get_guide_session_current_endpoint(
    guide_session_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    guide_session_current = await get_guide_session_current(session, guide_session_id)
    if guide_session_current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guide session not found")

    return success_response(guide_session_current.model_dump())
