# schemas.py 定义 Guide 模块的输入输出结构。
# 阅读这份文件有助于你先建立“这个模块传什么数据”的感觉。
from typing import Any

from pydantic import BaseModel, Field


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


class GuideAssetRead(BaseModel):
    guide_session_id: str
    playback_state: str
    asset_status: str
    summary: str | None
    stops: list[str] = Field(default_factory=list)
    result: dict[str, Any] | None = None


class GuidePlaybackUpdateRequest(BaseModel):
    action: str


class GuidePlaybackUpdateRead(BaseModel):
    guide_session_id: str
    playback_state: str
