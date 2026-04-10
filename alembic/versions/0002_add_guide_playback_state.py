"""add guide playback state

Revision ID: 0002_add_guide_playback_state
Revises: 0001_initial_core_schema
Create Date: 2026-04-10 11:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_add_guide_playback_state"
down_revision = "0001_initial_core_schema"
branch_labels = None
depends_on = None


guide_playback_state = sa.Enum(
    "not_triggered",
    "triggered",
    "playing",
    "played",
    "skipped",
    name="guide_playback_state",
)


def upgrade() -> None:
    bind = op.get_bind()
    guide_playback_state.create(bind, checkfirst=True)
    op.add_column(
        "guide_sessions",
        sa.Column(
            "playback_state",
            guide_playback_state,
            nullable=False,
            server_default="not_triggered",
        ),
    )
    op.alter_column("guide_sessions", "playback_state", server_default=None)


def downgrade() -> None:
    op.drop_column("guide_sessions", "playback_state")
    bind = op.get_bind()
    guide_playback_state.drop(bind, checkfirst=True)
