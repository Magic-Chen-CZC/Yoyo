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


class MapPolylinePointRead(BaseModel):
    stop_id: str | None
    order: int
    latitude: float
    longitude: float


class NavigationSummaryRead(BaseModel):
    current_stop_index: int
    stop_count: int
    remaining_stop_count: int
    has_next_stop: bool


class MapSessionRead(BaseModel):
    guide_session_id: str
    markers: list[MapMarkerRead] = Field(default_factory=list)
    polyline: list[MapPolylinePointRead] = Field(default_factory=list)
    navigation_summary: NavigationSummaryRead
    current_position: dict[str, float] | None = None
    current_stop: MapMarkerRead | None = None
    next_stop: MapMarkerRead | None = None
