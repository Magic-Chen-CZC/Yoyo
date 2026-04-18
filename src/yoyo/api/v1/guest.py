from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.guest.service import create_guest_session

router = APIRouter(prefix="/guest")


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_guest_session_endpoint(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    guest_session = await create_guest_session(session)
    return success_response(guest_session.model_dump(), message="created")
