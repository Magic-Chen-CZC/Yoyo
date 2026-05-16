# schemas.py 定义 Guide 模块的输入输出结构。
# 阅读这份文件有助于你先建立“这个模块传什么数据”的感觉。
from typing import Any

from pydantic import BaseModel, Field


class GuideStopScriptStructured(BaseModel):
    stop_name: str
    narration: str
    why_it_matters: str
    visitor_tip: str


class GuideBundleStructured(BaseModel):
    intro: str
    outro: str
    card_headline: str
    card_highlights: list[str] = Field(default_factory=list)
    card_practical_tips: list[str] = Field(default_factory=list)
    stop_scripts: list[GuideStopScriptStructured] = Field(default_factory=list)


class CreateGuideGenerationJobRequest(BaseModel):
    itinerary_version_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class GuideGenerationJobRead(BaseModel):
    id: str
    itinerary_version_id: str
    job_type: str
    status: str
    asset_status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error_code: str | None
    error_message: str | None


class GuideAssetJobMetaRead(BaseModel):
    id: str | None = None
    status: str | None = None
    asset_status: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class GuideAssetRead(BaseModel):
    guide_session_id: str
    playback_state: str
    asset_status: str
    summary: str | None
    stops: list[str] = Field(default_factory=list)
    result: dict[str, Any] | None = None
    job: GuideAssetJobMetaRead | None = None


class GuidePlaybackUpdateRequest(BaseModel):
    action: str


class GuidePlaybackUpdateRead(BaseModel):
    guide_session_id: str
    playback_state: str


class GuideSegmentActionRequest(BaseModel):
    action: str


class GuideAudioSegmentRead(BaseModel):
    stop_id: str | None = None
    stop_name: str | None = None
    segment_index: int
    status: str
    url: str | None = None


class GuideSegmentCycleRead(BaseModel):
    guide_session_id: str
    stop_id: str | None = None
    stop_name: str | None = None
    action: str
    segments: list[str] = Field(default_factory=list)
    audio_segments: list[GuideAudioSegmentRead] = Field(default_factory=list)
    segment_count: int = 0
    more_content_available: bool = False
    guide_style: str | None = None
