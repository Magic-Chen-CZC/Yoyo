"""add guide style preference to user profiles

Revision ID: 0003_add_guide_style_preference_to_user_profiles
Revises: 0002_add_attractions_and_user_profiles
Create Date: 2026-04-11 11:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_add_guide_style_preference_to_user_profiles"
down_revision = "0002_add_attractions_and_user_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("guide_style_preference", sa.String(length=16), nullable=False, server_default="SJ"),
    )
    op.alter_column("user_profiles", "guide_style_preference", server_default=None)


def downgrade() -> None:
    op.drop_column("user_profiles", "guide_style_preference")
