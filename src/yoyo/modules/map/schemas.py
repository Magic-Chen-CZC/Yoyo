from pydantic import BaseModel, Field


class MapMarkerRead(BaseModel):
    id: str | None
    name: str | None
    category: str | None
    latitude: float
    longitude: float
    order: int
    is_current: bool
    is_next: bool
    is_completed: bool = False
    is_editable: bool = False
    short_intro: str | None = None
    highlights: list[str] = Field(default_factory=list)
    visitor_tip: str | None = None
    source_type: str | None = None
    comment_count: int = 0
    latest_comment_preview: str | None = None


class MapPolylinePointRead(BaseModel):
    stop_id: str | None
    order: int
    latitude: float
    longitude: float


class NavigationSummaryRead(BaseModel):
    current_stop_index: int
    stop_count: int
    remaining_stop_count: int
    completed_stop_count: int
    editable_from_stop_index: int
    has_next_stop: bool


class MapSessionRead(BaseModel):
    guide_session_id: str
    markers: list[MapMarkerRead] = Field(default_factory=list)
    polyline: list[MapPolylinePointRead] = Field(default_factory=list)
    navigation_summary: NavigationSummaryRead
    current_position: dict[str, float] | None = None
    current_stop: MapMarkerRead | None = None
    next_stop: MapMarkerRead | None = None
