from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yoyo.db.base import Base
from yoyo.modules.shared.enums import QAMessageRole, QAMessageValidationStatus


class QAMessage(Base):
    __tablename__ = "qa_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    guide_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("guide_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[QAMessageRole] = mapped_column(
        Enum(QAMessageRole, name="qa_message_role"),
        nullable=False,
    )
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    validation_status: Mapped[QAMessageValidationStatus] = mapped_column(
        Enum(QAMessageValidationStatus, name="qa_message_validation_status"),
        default=QAMessageValidationStatus.PENDING,
        nullable=False,
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    guide_session: Mapped["GuideSession"] = relationship(back_populates="qa_messages")
