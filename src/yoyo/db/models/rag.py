from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yoyo.db.base import Base


class RAGIndexRun(Base):
    __tablename__ = "rag_index_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    backend: Mapped[str] = mapped_column(String(64), nullable=False, default="llamaindex_pgvector")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    collection_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
