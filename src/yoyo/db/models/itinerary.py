from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yoyo.db.base import Base
from yoyo.modules.shared.enums import ItineraryStatus, ItineraryVersionStatus


class Itinerary(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city_code: Mapped[str] = mapped_column(String(64), default="beijing")
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ItineraryStatus] = mapped_column(
        Enum(ItineraryStatus, name="itinerary_status"),
        default=ItineraryStatus.DRAFT,
        nullable=False,
    )
    current_version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("itinerary_versions.id", name="fk_itineraries_current_version_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    versions: Mapped[list["ItineraryVersion"]] = relationship(
        back_populates="itinerary",
        foreign_keys="ItineraryVersion.itinerary_id",
        cascade="all, delete-orphan",
    )
    current_version: Mapped["ItineraryVersion | None"] = relationship(
        foreign_keys=[current_version_id],
        post_update=True,
    )


class ItineraryVersion(Base):
    __tablename__ = "itinerary_versions"
    __table_args__ = (UniqueConstraint("itinerary_id", "version_no", name="uq_itinerary_versions"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    itinerary_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(nullable=False)
    planner_input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[ItineraryVersionStatus] = mapped_column(
        Enum(ItineraryVersionStatus, name="itinerary_version_status"),
        default=ItineraryVersionStatus.DRAFT,
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    itinerary: Mapped[Itinerary] = relationship(back_populates="versions", foreign_keys=[itinerary_id])
    guide_generation_jobs: Mapped[list["GuideGenerationJob"]] = relationship(
        back_populates="itinerary_version",
        cascade="all, delete-orphan",
    )
