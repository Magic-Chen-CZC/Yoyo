from typing import Any, Literal

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
    cache_hit: bool = False
    cache_key: str | None = None
    cached_at: str | None = None
    cache_ttl_seconds: int | None = None
    info_type: str | None = None


class WeatherContext(BaseModel):
    location_name: str | None = None
    province: str | None = None
    city: str | None = None
    adcode: str | None = None
    weather: str | None = None
    temperature_celsius: str | None = None
    wind_direction: str | None = None
    wind_power: str | None = None
    humidity: str | None = None
    report_time: str | None = None
    source: str = "amap"
    status: str = "available"
    reason: str | None = None


class NavigationStep(BaseModel):
    instruction: str
    road: str | None = None
    orientation: str | None = None
    distance_meters: int | None = None
    duration_seconds: int | None = None
    action: str | None = None
    assistant_action: str | None = None
    polyline: str | None = None
    end_location: tuple[float, float] | None = None
    turn_location_text: str | None = None
    vehicle_type: Literal["bus", "subway", "rail", "unknown"] | None = None


class NavigationPlace(BaseModel):
    raw_text: str | None = None
    place_id: str | None = None
    name: str | None = None
    display_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    adcode: str | None = None
    source: Literal["registry", "mock_attraction", "gps", "geocode_candidate", "amap_candidate", "unresolved"] = "unresolved"
    confidence: float = 0.0
    reason: str | None = None


class NavigationClarificationCandidate(BaseModel):
    index: int
    raw_text: str | None = None
    place_id: str | None = None
    name: str
    display_name: str | None = None
    address: str | None = None
    district: str | None = None
    poi_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    adcode: str | None = None
    source: Literal["registry", "amap_candidate"] = "amap_candidate"
    confidence: float = 0.0
    reason: str | None = None


class NavigationPlaceClarification(BaseModel):
    raw_text: str | None = None
    target_role: Literal["origin", "destination"] = "destination"
    target_index: int = 0
    reason: str
    message: str | None = None
    candidates: list[NavigationClarificationCandidate] = Field(default_factory=list)
    slot_result: dict[str, Any] = Field(default_factory=dict)


class NavigationSlotPayload(BaseModel):
    origin: str | None = None
    destinations: list[str] = Field(default_factory=list)
    origin_place: NavigationPlace | None = None
    destination_places: list[NavigationPlace] = Field(default_factory=list)
    mode: Literal["walking", "driving", "transit"] = "walking"
    mode_source: Literal["explicit", "distance_default", "config_default", "fallback"] = "config_default"
    transit_preference: Literal["bus", "subway", "public_transport"] | None = None
    source: Literal["rule", "fallback"] = "rule"
    request_kind: Literal[
        "next_stop",
        "destination_only",
        "explicit_route",
        "multi_leg",
        "unknown",
    ] = "unknown"
    reason: str | None = None


class NavigationLeg(BaseModel):
    origin_name: str | None = None
    destination_name: str | None = None
    requested_mode: str | None = None
    provider_mode: str | None = None
    final_mode: str | None = None
    requested_transit_preference: str | None = None
    final_transit_vehicle_types: list[str] = Field(default_factory=list)
    mode_fallback_used: bool = False
    mode_fallback_reason: str | None = None
    provider_reason: str | None = None
    distance_meters: int | None = None
    duration_seconds: int | None = None
    steps: list[NavigationStep] = Field(default_factory=list)
    status: str = "available"
    reason: str | None = None


class NavigationContext(BaseModel):
    origin_name: str | None = None
    destination_name: str | None = None
    mode: str = "walking"
    requested_mode: str | None = None
    final_mode: str | None = None
    requested_transit_preference: str | None = None
    final_transit_vehicle_types: list[str] = Field(default_factory=list)
    mode_fallback_used: bool = False
    mode_fallback_reason: str | None = None
    distance_meters: int | None = None
    duration_seconds: int | None = None
    steps: list[NavigationStep] = Field(default_factory=list)
    legs: list[NavigationLeg] = Field(default_factory=list)
    slot_result: NavigationSlotPayload | None = None
    clarification: NavigationPlaceClarification | None = None
    source: str = "amap"
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
    weather: WeatherContext | None = None
    navigation: NavigationContext | None = None
    rag: RAGContext | None = None
    prompt_safe_attraction: dict[str, Any] = Field(default_factory=dict)
    prompt_safe_profile: dict[str, Any] = Field(default_factory=dict)
    session_context: dict[str, Any] = Field(default_factory=dict)
    dialogue_history: list[dict[str, Any]] = Field(default_factory=list)
    build_debug: dict[str, Any] = Field(default_factory=dict)
