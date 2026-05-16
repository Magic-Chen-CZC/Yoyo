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


class GuideSessionLifecycleRead(BaseModel):
    guide_session_id: str
    status: str
    playback_state: str


class SessionCurrentRead(BaseModel):
    guide_session_id: str
    itinerary_id: str
    itinerary_version_id: str
    city_code: str | None = None
    status: str
    playback_state: str
    current_stop_index: int
    has_next_stop: bool
    current_stop: dict[str, Any] | None
    next_stop: dict[str, Any] | None
    current_position: dict[str, float] | None
    stop_count: int
    completed_stop_count: int
    editable_from_stop_index: int
    frozen_stop_ids: list[str] = Field(default_factory=list)
    editable_stop_ids: list[str] = Field(default_factory=list)
    plan_summary: str | None


class GPSUpdateRequest(BaseModel):
    latitude: float
    longitude: float


class GPSUpdateRead(BaseModel):
    guide_session_id: str
    current_position: dict[str, float]
    current_stop_index: int
    current_stop: dict[str, Any] | None
    distance_to_current_stop_meters: float | None
    arrival_threshold_meters: float | None
    arrived: bool
