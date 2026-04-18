from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.share_card.service import build_share_card

router = APIRouter(prefix="/share-card")


@router.get("/session/{guide_session_id}")
async def get_session_share_card(
    guide_session_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    share_card = await build_share_card(session, guide_session_id)
    if share_card is None:
        raise HTTPException(status_code=404, detail="guide session not found")
    return success_response(share_card.model_dump())
