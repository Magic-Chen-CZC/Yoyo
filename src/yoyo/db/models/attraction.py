from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yoyo.db.base import Base


class Attraction(Base):
    __tablename__ = "attractions"
    __table_args__ = (UniqueConstraint("city_code", "name", name="uq_attractions_city_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    city_code: Mapped[str] = mapped_column(String(64), default="beijing", nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="attraction")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    short_intro: Mapped[str] = mapped_column(Text, nullable=False, default="")
    history: Mapped[str] = mapped_column(Text, nullable=False, default="")
    highlights_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    visitor_tips_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    practical_notes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    family_friendly_notes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    photo_spot_notes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    guide_segments_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
