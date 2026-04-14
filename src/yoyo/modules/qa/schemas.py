from typing import Any

from pydantic import BaseModel, Field


class QAAskRequest(BaseModel):
    guide_session_id: str | None = None
    user_id: str | None = None
    query: str
    language: str = "en"
    context: dict[str, Any] = Field(default_factory=dict)


class SessionAwareContext(BaseModel):
    guide_session_id: str | None
    itinerary_version_id: str | None
    current_stop_name: str | None = None
    stop_count: int | None = None
    user_id: str | None = None


class PlannerHandoffPayload(BaseModel):
    intent: str = "planner_handoff"
    operation: str
    target: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class QAAskResponse(BaseModel):
    supported: bool
    intent: str
    answer: str
    used_skills: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
