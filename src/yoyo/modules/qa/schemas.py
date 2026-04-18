from typing import Any, Literal

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


class QAAskStructuredBase(BaseModel):
    answer: str
    status: Literal["ok", "degraded", "unavailable", "clarification", "redirect"]
    reason: str | None = None


class TranslationStructuredAnswer(QAAskStructuredBase):
    mode: Literal["direct_translation", "needs_phrase", "degraded"]


class LiveInfoStructuredAnswer(QAAskStructuredBase):
    not_confirmed: bool = True
    confidence: Literal["low", "medium", "high"] = "low"


class TripAssistantStructuredAnswer(QAAskStructuredBase):
    route_focus: Literal[
        "current_stop",
        "next_stop",
        "route_overview",
        "manual_edit_redirect",
        "general_guidance",
    ]
    references_current_stop: bool = False
    references_next_stop: bool = False


class AttractionExplainStructuredAnswer(QAAskStructuredBase):
    grounding: Literal["sql", "rag", "sql_then_rag", "limited"]
    includes_history: bool = False
    includes_tips: bool = False


class QAAskResponse(BaseModel):
    supported: bool
    intent: str
    answer: str
    used_skills: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
