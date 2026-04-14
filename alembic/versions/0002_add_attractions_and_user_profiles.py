"""add attractions and user profiles

Revision ID: 0002_add_attractions_and_user_profiles
Revises: 0001_initial_core_schema
Create Date: 2026-04-10 16:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_attractions_and_user_profiles"
down_revision = "0001_initial_core_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attractions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("city_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("aliases_json", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("recommended_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("short_intro", sa.Text(), nullable=False),
        sa.Column("history", sa.Text(), nullable=False),
        sa.Column("highlights_json", sa.JSON(), nullable=False),
        sa.Column("visitor_tips_json", sa.JSON(), nullable=False),
        sa.Column("practical_notes_json", sa.JSON(), nullable=False),
        sa.Column("family_friendly_notes_json", sa.JSON(), nullable=False),
        sa.Column("photo_spot_notes_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("city_code", "name", name="uq_attractions_city_name"),
    )
    op.create_index("ix_attractions_city_code_name", "attractions", ["city_code", "name"])

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=255), primary_key=True),
        sa.Column("preferred_language", sa.String(length=32), nullable=False),
        sa.Column("interests_json", sa.JSON(), nullable=False),
        sa.Column("travel_style", sa.String(length=64), nullable=False),
        sa.Column("walking_preference", sa.String(length=64), nullable=False),
        sa.Column("pace_preference", sa.String(length=64), nullable=False),
        sa.Column("audience_type", sa.String(length=64), nullable=False),
        sa.Column("answer_length_preference", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
    op.drop_index("ix_attractions_city_code_name", table_name="attractions")
    op.drop_table("attractions")
