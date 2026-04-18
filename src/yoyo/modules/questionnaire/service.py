from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.profile import UserProfile
from yoyo.db.models.questionnaire import QuestionnaireSubmission
from yoyo.modules.questionnaire.profile_mapper import map_answers_to_profile_fields
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
        payload_json=payload.to_payload(),
    )
    session.add(submission)

    if payload.user_id is not None:
        profile_fields = map_answers_to_profile_fields(payload.answers)
        profile = await session.get(UserProfile, payload.user_id)
        if profile is None:
            profile = UserProfile(user_id=payload.user_id, **profile_fields)
            session.add(profile)
        else:
            for key, value in profile_fields.items():
                setattr(profile, key, value)

    await session.commit()
    await session.refresh(submission)

    return QuestionnaireSubmissionRead(
        id=submission.id,
        user_id=submission.user_id,
        source=submission.source,
        status=submission.status.value,
        payload=submission.payload_json,
    )
