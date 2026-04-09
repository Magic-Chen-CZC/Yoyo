from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.session.schemas import GPSUpdateRequest
from yoyo.modules.session.service import update_gps_position

router = APIRouter(prefix="/gps")


@router.post("/update/{guide_session_id}")
async def update_gps(
    guide_session_id: str,
    payload: GPSUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    gps = await update_gps_position(session, guide_session_id, payload.latitude, payload.longitude)
    if gps is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guide session not found")

    return success_response(gps.model_dump())
