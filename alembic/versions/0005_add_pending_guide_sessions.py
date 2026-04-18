"""add pending guide sessions

Revision ID: 0005_add_pending_guide_sessions
Revises: 0004_add_guest_users_and_profile_sources
Create Date: 2026-04-14 18:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_pending_guide_sessions"
down_revision = "0004_add_guest_users_and_profile_sources"
branch_labels = None
depends_on = None


old_guide_session_status = sa.Enum("active", "finished", name="guide_session_status")
new_guide_session_status = sa.Enum("pending", "active", "finished", name="guide_session_status")
old_itinerary_status = sa.Enum("draft", "active", name="itinerary_status")
new_itinerary_status = sa.Enum("draft", "ready", "active", "completed", name="itinerary_status")


def upgrade() -> None:
    op.execute("ALTER TYPE guide_session_status ADD VALUE IF NOT EXISTS 'pending' BEFORE 'active'")
    op.execute("ALTER TYPE itinerary_status ADD VALUE IF NOT EXISTS 'ready' AFTER 'draft'")
    op.execute("ALTER TYPE itinerary_status ADD VALUE IF NOT EXISTS 'completed' AFTER 'active'")


def downgrade() -> None:
    op.execute("ALTER TYPE guide_session_status RENAME TO guide_session_status_old")
    old_guide_session_status.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE guide_sessions ALTER COLUMN status TYPE guide_session_status "
        "USING status::text::guide_session_status"
    )
    op.execute("DROP TYPE guide_session_status_old")

    op.execute("ALTER TYPE itinerary_status RENAME TO itinerary_status_old")
    old_itinerary_status.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE itineraries ALTER COLUMN status TYPE itinerary_status "
        "USING status::text::itinerary_status"
    )
    op.execute("DROP TYPE itinerary_status_old")
