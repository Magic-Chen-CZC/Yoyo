# QA service 是一层很薄的中转层。
# 它的意义主要是把 API 层和真正的 QA 编排逻辑分开。
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.modules.qa.orchestrator import answer_question
from yoyo.modules.qa.schemas import QAAskRequest, QAAskResponse


async def ask_question(session: AsyncSession, payload: QAAskRequest) -> QAAskResponse:
    return await answer_question(session, payload)
