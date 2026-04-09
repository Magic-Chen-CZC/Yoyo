from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from yoyo.db.base import Base
from yoyo.modules.shared.enums import QuestionnaireSubmissionStatus


class QuestionnaireSubmission(Base):
    __tablename__ = "questionnaire_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="questionnaire")
    status: Mapped[QuestionnaireSubmissionStatus] = mapped_column(
        Enum(QuestionnaireSubmissionStatus, name="questionnaire_submission_status"),
        default=QuestionnaireSubmissionStatus.SUBMITTED,
        nullable=False,
    )
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
