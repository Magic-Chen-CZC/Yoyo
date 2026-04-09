from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.questionnaire.schemas import (
    QuestionnaireSubmissionCreate,
    QuestionnaireSubmissionRead,
)
from yoyo.modules.questionnaire.service import create_questionnaire_submission

router = APIRouter(prefix="/questionnaire")


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def create_submission(
    payload: QuestionnaireSubmissionCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    submission = await create_questionnaire_submission(session, payload)
    return success_response(submission.model_dump(), message="created")
