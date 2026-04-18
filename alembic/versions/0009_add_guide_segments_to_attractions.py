"""add guide segments to attractions

Revision ID: 0009_add_guide_segments_to_attractions
Revises: 0008_add_rag_index_runs
Create Date: 2026-04-15 00:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_add_guide_segments_to_attractions"
down_revision = "0008_add_rag_index_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attractions",
        sa.Column("guide_segments_json", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.alter_column("attractions", "guide_segments_json", server_default=None)


def downgrade() -> None:
    op.drop_column("attractions", "guide_segments_json")
