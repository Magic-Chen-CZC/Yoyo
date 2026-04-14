from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from yoyo.db.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    preferred_language: Mapped[str] = mapped_column(String(32), default="en", nullable=False)
    interests_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    travel_style: Mapped[str] = mapped_column(String(64), default="balanced", nullable=False)
    walking_preference: Mapped[str] = mapped_column(String(64), default="moderate", nullable=False)
    pace_preference: Mapped[str] = mapped_column(String(64), default="balanced", nullable=False)
    audience_type: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    answer_length_preference: Mapped[str] = mapped_column(String(64), default="medium", nullable=False)
    guide_style_preference: Mapped[str] = mapped_column(String(16), default="SJ", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
