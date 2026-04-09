from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.questionnaire import QuestionnaireSubmission
from yoyo.modules.questionnaire.schemas import (
    QuestionnaireSubmissionCreate,
    QuestionnaireSubmissionRead,
)


async def create_questionnaire_submission(
    session: AsyncSession, payload: QuestionnaireSubmissionCreate
) -> QuestionnaireSubmissionRead:
    submission = QuestionnaireSubmission(
        user_id=payload.user_id,
        source=payload.source,
        payload_json=payload.payload,
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)

    return QuestionnaireSubmissionRead(
        id=submission.id,
        user_id=submission.user_id,
        source=submission.source,
        status=submission.status.value,
        payload=submission.payload_json,
    )
