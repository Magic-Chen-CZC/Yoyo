"""add poi comments

Revision ID: 0006_add_poi_comments
Revises: 0005_add_pending_guide_sessions
Create Date: 2026-04-14 22:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_add_poi_comments"
down_revision = "0005_add_pending_guide_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "poi_comments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("stop_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("guide_session_id", sa.String(length=36), sa.ForeignKey("guide_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_poi_comments_stop_id_created_at", "poi_comments", ["stop_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_poi_comments_stop_id_created_at", table_name="poi_comments")
    op.drop_table("poi_comments")
