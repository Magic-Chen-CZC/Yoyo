from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.qa.schemas import QAAskRequest
from yoyo.modules.qa.service import ask_question

# QA API 的入口文件。
# 这个文件本身很薄，主要职责是：收请求 -> 调用 QA service -> 返回统一响应。
router = APIRouter(prefix="/qa")


# QA 的主入口：接收用户问题，并交给问答编排层处理。
@router.post("/ask")
async def ask_qa(
    payload: QAAskRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    response = await ask_question(session, payload)
    return success_response(response.model_dump())
