from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yoyo.db.base import Base
from yoyo.db.enums import db_enum
from yoyo.modules.shared.enums import GuidePlaybackState, GuideSessionStatus

if TYPE_CHECKING:
    from yoyo.db.models.qa import QAMessage


class GuideSession(Base):
    __tablename__ = "guide_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    itinerary_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
    )
    itinerary_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("itinerary_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[GuideSessionStatus] = mapped_column(
        db_enum(GuideSessionStatus, name="guide_session_status"),
        default=GuideSessionStatus.PENDING,
        nullable=False,
    )
    playback_state: Mapped[GuidePlaybackState] = mapped_column(
        db_enum(GuidePlaybackState, name="guide_playback_state"),
        default=GuidePlaybackState.NOT_TRIGGERED,
        nullable=False,
    )
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    qa_messages: Mapped[list[QAMessage]] = relationship(
        back_populates="guide_session",
        cascade="all, delete-orphan",
    )
