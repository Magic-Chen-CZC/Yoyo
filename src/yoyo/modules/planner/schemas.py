from typing import Any

from pydantic import BaseModel, Field


class CreateItineraryRequest(BaseModel):
    user_id: str | None = None
    city_code: str = "beijing"
    title: str | None = None
    questionnaire_submission_id: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)


class ItineraryVersionRead(BaseModel):
    id: str
    version_no: int
    status: str
    planner_input: dict[str, Any]
    plan: dict[str, Any]


class ItineraryRead(BaseModel):
    id: str
    user_id: str | None
    city_code: str
    title: str | None
    status: str
    current_version_id: str | None
    version: ItineraryVersionRead
