"""add rag index runs

Revision ID: 0008_add_rag_index_runs
Revises: 0007_enable_pgvector_extension
Create Date: 2026-04-15 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_add_rag_index_runs"
down_revision = "0007_enable_pgvector_extension"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_index_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("backend", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=True),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("collection_name", sa.String(length=128), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("rag_index_runs")
