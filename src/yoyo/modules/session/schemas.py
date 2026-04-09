from typing import Any

from pydantic import BaseModel, Field


class CreateGuideSessionRequest(BaseModel):
    itinerary_id: str
    itinerary_version_id: str
    context: dict[str, Any] = Field(default_factory=dict)


class GuideSessionRead(BaseModel):
    id: str
    itinerary_id: str
    itinerary_version_id: str
    status: str
    context: dict[str, Any]


class SessionCurrentRead(BaseModel):
    guide_session_id: str
    itinerary_id: str
    itinerary_version_id: str
    status: str
    playback_state: str
    current_stop: dict[str, Any] | None
    next_stop: dict[str, Any] | None
    current_position: dict[str, float] | None
    stop_count: int
    plan_summary: str | None


class GPSUpdateRequest(BaseModel):
    latitude: float
    longitude: float


class GPSUpdateRead(BaseModel):
    guide_session_id: str
    current_position: dict[str, float]
    current_stop: dict[str, Any] | None
    arrived: bool
