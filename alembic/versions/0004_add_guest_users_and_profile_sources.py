"""add guest users and profile sources

Revision ID: 0004_add_guest_users_and_profile_sources
Revises: 0003_add_guide_style_preference_to_user_profiles
Create Date: 2026-04-14 15:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_guest_users_and_profile_sources"
down_revision = "0003_add_guide_style_preference_to_user_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guest_users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("anonymous_token", sa.String(length=64), nullable=False, unique=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.add_column(
        "user_profiles",
        sa.Column("profile_source", sa.String(length=64), nullable=False, server_default="questionnaire_flow"),
    )
    op.add_column(
        "user_profiles",
        sa.Column("profile_version", sa.String(length=32), nullable=False, server_default="v1"),
    )
    op.alter_column("user_profiles", "profile_source", server_default=None)
    op.alter_column("user_profiles", "profile_version", server_default=None)


def downgrade() -> None:
    op.drop_column("user_profiles", "profile_version")
    op.drop_column("user_profiles", "profile_source")
    op.drop_table("guest_users")
