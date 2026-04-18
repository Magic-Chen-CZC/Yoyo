from pydantic import BaseModel, Field


class TripSummaryRead(BaseModel):
    itinerary_title: str | None = None
    stop_count: int = 0
    stops_preview: list[str] = Field(default_factory=list)
    completed_at: str | None = None


class SocialSummaryRead(BaseModel):
    comment_count_total: int = 0
    featured_comment_preview: str | None = None
    top_commented_stop_name: str | None = None


class MapPreviewRead(BaseModel):
    polyline: list[dict[str, object]] = Field(default_factory=list)
    markers_preview: list[dict[str, object]] = Field(default_factory=list)


class ShareCardRead(BaseModel):
    guide_session_id: str
    status: str
    is_shareable: bool
    headline: str
    subheadline: str | None = None
    highlights: list[str] = Field(default_factory=list)
    route_style: str | None = None
    guide_style: str | None = None
    practical_tips: list[str] = Field(default_factory=list)
    trip_summary: TripSummaryRead
    social_summary: SocialSummaryRead
    map_preview: MapPreviewRead
