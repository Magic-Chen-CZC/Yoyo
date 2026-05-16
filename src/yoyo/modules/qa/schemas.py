from typing import Any, Literal

from pydantic import BaseModel, Field


QAIntent = Literal[
    "translation",
    "live_info",
    "weather_info",
    "navigation_text",
    "trip_assistant",
    "attraction_explain",
    "manual_route_edit_redirect",
    "smalltalk",
    "out_of_scope",
]
BoundaryTopic = Literal["traffic", "crowd"]
OutOfScopeSubtype = Literal[
    "general_out_of_scope",
    "traffic_boundary",
    "crowd_boundary",
    "low_confidence_unclassified",
    "weak_travel_adjacent_unclassified",
]


class QAAskRequest(BaseModel):
    guide_session_id: str | None = None
    user_id: str | None = None
    query: str
    language: str = "en"
    llm_provider: str | None = None
    llm_model: str | None = None
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


class DomainGuardResult(BaseModel):
    supported: bool
    hard_deny: bool
    deny_reason: str | None = None
    matched_signals: list[str] = Field(default_factory=list)


class IntentRouterResult(BaseModel):
    intent: QAIntent
    confidence: float
    margin: float
    needs_fallback: bool
    fallback_reason: str | None = None
    signals: list[str] = Field(default_factory=list)
    candidates: dict[str, float] = Field(default_factory=dict)
    runner_up_intent: QAIntent | None = None
    last_intent: QAIntent | None = None
    boundary_topic: BoundaryTopic | None = None
    out_of_scope_subtype: OutOfScopeSubtype | None = None


NavigationRequestKind = Literal[
    "next_stop",
    "destination_only",
    "explicit_route",
    "multi_leg",
    "unknown",
]
NavigationSlotSource = Literal["rule", "fallback"]
NavigationMode = Literal["walking", "driving", "transit"]
NavigationModeSource = Literal["explicit", "distance_default", "config_default", "fallback"]
NavigationTransitPreference = Literal["bus", "subway", "public_transport"]


class NavigationResolvedPlace(BaseModel):
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


class NavigationSlotResult(BaseModel):
    origin: str | None = None
    destinations: list[str] = Field(default_factory=list)
    origin_place: NavigationResolvedPlace | None = None
    destination_places: list[NavigationResolvedPlace] = Field(default_factory=list)
    mode: NavigationMode = "walking"
    mode_source: NavigationModeSource = "config_default"
    transit_preference: NavigationTransitPreference | None = None
    source: NavigationSlotSource = "rule"
    request_kind: NavigationRequestKind = "unknown"
    reason: str | None = None


class WeatherSlotResult(BaseModel):
    location_name: str | None = None
    source: Literal["fallback"] = "fallback"
    reason: str | None = None


class IntentRouterFallbackResult(BaseModel):
    intent: QAIntent
    confidence: float
    reason: str | None = None
    used_translation_pivot: bool = False
    pivot_query: str | None = None
    weather_location_name: str | None = None
    slots: NavigationSlotResult | None = None
    clarification_action: Literal["selected", "needs_clarification", "not_a_selection"] | None = None
    selected_index: int | None = None


class TranslationStructuredAnswer(QAAskStructuredBase):
    mode: Literal["direct_translation", "needs_phrase", "degraded"]


class LiveInfoStructuredAnswer(QAAskStructuredBase):
    not_confirmed: bool = True
    confidence: Literal["low", "medium", "high"] = "low"


class WeatherInfoStructuredAnswer(QAAskStructuredBase):
    pass


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
    grounding: Literal["sql", "rag", "sql_then_rag", "model_knowledge", "limited"]
    includes_history: bool = False
    includes_tips: bool = False


class QAAskResponse(BaseModel):
    supported: bool
    intent: str
    answer: str
    used_skills: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QAResolvedQuery(BaseModel):
    raw_query: str
    effective_query: str
    user_language: str
    processing_language: str = "zh"
    used_translation_pivot: bool = False
    pivot_query: str | None = None
