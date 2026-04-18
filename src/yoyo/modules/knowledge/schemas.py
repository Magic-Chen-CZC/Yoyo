from typing import Any

from pydantic import BaseModel, Field


class AttractionContext(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: str
    latitude: float | None = None
    longitude: float | None = None
    recommended_duration_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    short_intro: str = ""
    history: str = ""
    highlights: list[str] = Field(default_factory=list)
    visitor_tips: list[str] = Field(default_factory=list)
    practical_notes: list[str] = Field(default_factory=list)
    family_friendly_notes: list[str] = Field(default_factory=list)
    photo_spot_notes: list[str] = Field(default_factory=list)
    guide_segments: list[str] = Field(default_factory=list)
    source: str = "sql"


class ProfileContext(BaseModel):
    user_id: str
    preferred_language: str = "en"
    interests: list[str] = Field(default_factory=list)
    travel_style: str = "balanced"
    walking_preference: str = "moderate"
    pace_preference: str = "balanced"
    audience_type: str = "general"
    answer_length_preference: str = "medium"
    guide_style_preference: str = "SJ"
    source: str = "sql"


class LiveInfoContext(BaseModel):
    summary: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str | None = None
    confidence: str = "low"
    not_confirmed: bool = False
    source: str = "live_search"
    status: str = "available"
    reason: str | None = None


class RAGChunk(BaseModel):
    chunk_id: str
    text: str
    source: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGContext(BaseModel):
    chunks: list[RAGChunk] = Field(default_factory=list)
    retrieval_mode: str = "disabled"
    fallback_used: bool = False


class HybridContext(BaseModel):
    attraction: AttractionContext | None = None
    profile: ProfileContext | None = None
    live_info: LiveInfoContext | None = None
    rag: RAGContext | None = None
    prompt_safe_attraction: dict[str, Any] = Field(default_factory=dict)
    prompt_safe_profile: dict[str, Any] = Field(default_factory=dict)
    session_context: dict[str, Any] = Field(default_factory=dict)
    dialogue_history: list[dict[str, Any]] = Field(default_factory=list)
