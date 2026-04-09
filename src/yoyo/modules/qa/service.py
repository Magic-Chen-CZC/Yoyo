from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.modules.qa.orchestrator import answer_question
from yoyo.modules.qa.schemas import QAAskRequest, QAAskResponse


async def ask_question(session: AsyncSession, payload: QAAskRequest) -> QAAskResponse:
    return await answer_question(session, payload)
