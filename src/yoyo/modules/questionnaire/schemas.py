from typing import Any

from pydantic import BaseModel, Field


class QuestionnaireSubmissionCreate(BaseModel):
    user_id: str | None = None
    source: str = "questionnaire"
    payload: dict[str, Any] = Field(default_factory=dict)


class QuestionnaireSubmissionRead(BaseModel):
    id: str
    user_id: str | None
    source: str
    status: str
    payload: dict[str, Any]
