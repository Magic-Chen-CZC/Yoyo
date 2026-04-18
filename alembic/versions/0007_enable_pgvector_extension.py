"""enable pgvector extension

Revision ID: 0007_enable_pgvector_extension
Revises: 0006_add_poi_comments
Create Date: 2026-04-14 23:05:00
"""

from alembic import op


revision = "0007_enable_pgvector_extension"
down_revision = "0006_add_poi_comments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
