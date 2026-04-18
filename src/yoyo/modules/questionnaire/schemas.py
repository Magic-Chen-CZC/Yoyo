from typing import Any

from pydantic import BaseModel, Field, model_validator

from yoyo.modules.questionnaire.flow import (
    ALLOWED_OPTIONS,
    DEFAULT_GUIDE_ROLE,
    MULTI_SELECT_IDS,
    QUESTIONNAIRE_FLOW_VERSION,
    QUESTION_IDS,
    SINGLE_SELECT_IDS,
    get_questionnaire_flow,
)


class QuestionnaireSubmissionCreate(BaseModel):
    user_id: str | None = None
    source: str = "questionnaire"
    role_choice: str = DEFAULT_GUIDE_ROLE
    flow_version: str = QUESTIONNAIRE_FLOW_VERSION
    answers: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_answers(self) -> "QuestionnaireSubmissionCreate":
        normalized_answers = {**self.answers, "guide_role": self.role_choice}
        unknown_questions = set(normalized_answers) - QUESTION_IDS
        if unknown_questions:
            raise ValueError(f"unknown questionnaire answers: {sorted(unknown_questions)}")

        missing_questions = QUESTION_IDS - set(normalized_answers)
        if missing_questions:
            raise ValueError(f"missing questionnaire answers: {sorted(missing_questions)}")

        for question_id in SINGLE_SELECT_IDS:
            value = normalized_answers.get(question_id)
            if not isinstance(value, str) or value not in ALLOWED_OPTIONS[question_id]:
                raise ValueError(f"invalid answer for {question_id}")

        for question_id in MULTI_SELECT_IDS:
            value = normalized_answers.get(question_id)
            if not isinstance(value, list) or not value:
                raise ValueError(f"invalid answer for {question_id}")
            allowed = ALLOWED_OPTIONS[question_id]
            if any(not isinstance(item, str) or item not in allowed for item in value):
                raise ValueError(f"invalid answer for {question_id}")

        self.answers = normalized_answers
        return self

    def to_payload(self) -> dict[str, Any]:
        return {
            "flow_version": self.flow_version,
            "role_choice": self.role_choice,
            "answers": self.answers,
        }


class QuestionnaireSubmissionRead(BaseModel):
    id: str
    user_id: str | None
    source: str
    status: str
    payload: dict[str, Any]


class QuestionnaireFlowRead(BaseModel):
    version: str
    question_count: int
    questions: list[dict[str, Any]] = Field(default_factory=list)


def build_questionnaire_flow_read() -> QuestionnaireFlowRead:
    return QuestionnaireFlowRead.model_validate(get_questionnaire_flow())
