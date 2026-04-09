from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.qa.schemas import QAAskRequest
from yoyo.modules.qa.service import ask_question

router = APIRouter(prefix="/qa")


@router.post("/ask")
async def ask_qa(
    payload: QAAskRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    response = await ask_question(session, payload)
    return success_response(response.model_dump())
