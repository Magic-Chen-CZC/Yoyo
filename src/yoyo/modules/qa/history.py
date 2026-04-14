from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.qa import QAMessage
from yoyo.modules.shared.enums import QAMessageRole, QAMessageValidationStatus


async def load_recent_history(
    session: AsyncSession, guide_session_id: str | None, limit: int = 6
) -> list[dict[str, object]]:
    if guide_session_id is None:
        return []

    result = await session.execute(
        select(QAMessage)
        .where(QAMessage.guide_session_id == guide_session_id)
        .order_by(QAMessage.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return [
        {
            "role": message.role.value,
            "intent": message.intent,
            "content": message.content,
            "metadata": message.metadata_json,
            "validation_status": message.validation_status.value,
        }
        for message in messages
    ]


async def append_user_message(
    session: AsyncSession,
    *,
    guide_session_id: str | None,
    intent: str | None,
    content: str,
    metadata: dict[str, object],
) -> None:
    if guide_session_id is None:
        return
    session.add(
        QAMessage(
            guide_session_id=guide_session_id,
            role=QAMessageRole.USER,
            intent=intent,
            content=content,
            validation_status=QAMessageValidationStatus.PASSED,
            metadata_json=metadata,
        )
    )
    await session.commit()


async def append_assistant_message(
    session: AsyncSession,
    *,
    guide_session_id: str | None,
    intent: str,
    content: str,
    metadata: dict[str, object],
    valid: bool,
) -> None:
    if guide_session_id is None:
        return
    session.add(
        QAMessage(
            guide_session_id=guide_session_id,
            role=QAMessageRole.ASSISTANT,
            intent=intent,
            content=content,
            validation_status=QAMessageValidationStatus.PASSED if valid else QAMessageValidationStatus.FAILED,
            metadata_json=metadata,
        )
    )
    await session.commit()
