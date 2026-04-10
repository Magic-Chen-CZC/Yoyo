from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yoyo.db.base import Base
from yoyo.db.enums import db_enum
from yoyo.modules.shared.enums import (
    AssetStatus,
    GuideGenerationJobStatus,
    GuideGenerationJobType,
)

if TYPE_CHECKING:
    from yoyo.db.models.itinerary import ItineraryVersion


class GuideGenerationJob(Base):
    __tablename__ = "guide_generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    itinerary_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("itinerary_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_type: Mapped[GuideGenerationJobType] = mapped_column(
        db_enum(GuideGenerationJobType, name="guide_generation_job_type"),
        default=GuideGenerationJobType.GUIDE_BUNDLE,
        nullable=False,
    )
    status: Mapped[GuideGenerationJobStatus] = mapped_column(
        db_enum(GuideGenerationJobStatus, name="guide_generation_job_status"),
        default=GuideGenerationJobStatus.PENDING,
        nullable=False,
    )
    asset_status: Mapped[AssetStatus] = mapped_column(
        db_enum(AssetStatus, name="asset_status"),
        default=AssetStatus.PENDING,
        nullable=False,
    )
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    itinerary_version: Mapped[ItineraryVersion] = relationship(
        back_populates="guide_generation_jobs"
    )
