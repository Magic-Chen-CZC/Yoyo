from typing import Any

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    user_id: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)


class RecommendationRead(BaseModel):
    recommendation_id: str
    title: str
    summary: str
    entry_type: str
    template_id: str | None = None
    selected_poi_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
