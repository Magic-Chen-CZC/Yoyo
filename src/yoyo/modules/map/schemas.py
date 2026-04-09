from typing import Any

from pydantic import BaseModel, Field


class MapSessionRead(BaseModel):
    guide_session_id: str
    markers: list[dict[str, Any]] = Field(default_factory=list)
    polyline: list[dict[str, float]] = Field(default_factory=list)
    current_position: dict[str, float] | None = None
    current_stop: dict[str, Any] | None = None
    next_stop: dict[str, Any] | None = None
