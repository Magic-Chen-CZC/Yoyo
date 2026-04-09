from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yoyo.db.base import Base
from yoyo.modules.shared.enums import GuidePlaybackState, GuideSessionStatus


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
        Enum(GuideSessionStatus, name="guide_session_status"),
        default=GuideSessionStatus.ACTIVE,
        nullable=False,
    )
    playback_state: Mapped[GuidePlaybackState] = mapped_column(
        Enum(GuidePlaybackState, name="guide_playback_state"),
        default=GuidePlaybackState.NOT_TRIGGERED,
        nullable=False,
    )
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    qa_messages: Mapped[list["QAMessage"]] = relationship(
        back_populates="guide_session",
        cascade="all, delete-orphan",
    )
