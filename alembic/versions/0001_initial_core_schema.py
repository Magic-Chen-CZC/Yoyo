"""initial core schema

Revision ID: 0001_initial_core_schema
Revises: None
Create Date: 2026-04-08 15:50:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_core_schema"
down_revision = None
branch_labels = None
depends_on = None


questionnaire_submission_status = sa.Enum("submitted", "processed", name="questionnaire_submission_status")
itinerary_status = sa.Enum("draft", "active", name="itinerary_status")
itinerary_version_status = sa.Enum("draft", "active", "archived", name="itinerary_version_status")
guide_generation_job_type = sa.Enum("guide_bundle", name="guide_generation_job_type")
guide_generation_job_status = sa.Enum(
    "pending", "queued", "running", "succeeded", "failed", "cancelled", name="guide_generation_job_status"
)
asset_status = sa.Enum("missing", "pending", "ready", "failed", "stale", name="asset_status")
guide_session_status = sa.Enum("active", "finished", name="guide_session_status")
qa_message_role = sa.Enum("user", "assistant", "system", name="qa_message_role")
qa_message_validation_status = sa.Enum("pending", "passed", "failed", name="qa_message_validation_status")


def upgrade() -> None:
    op.create_table(
        "questionnaire_submissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", questionnaire_submission_status, nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "itineraries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("city_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", itinerary_status, nullable=False),
        sa.Column("current_version_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "itinerary_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("itinerary_id", sa.String(length=36), sa.ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("planner_input_json", sa.JSON(), nullable=False),
        sa.Column("plan_json", sa.JSON(), nullable=False),
        sa.Column("status", itinerary_version_status, nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("itinerary_id", "version_no", name="uq_itinerary_versions"),
    )

    op.create_foreign_key(
        "fk_itineraries_current_version_id",
        "itineraries",
        "itinerary_versions",
        ["current_version_id"],
        ["id"],
    )
    op.create_index("ix_itineraries_current_version_id", "itineraries", ["current_version_id"])

    op.create_table(
        "guide_generation_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "itinerary_version_id",
            sa.String(length=36),
            sa.ForeignKey("itinerary_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_type", guide_generation_job_type, nullable=False),
        sa.Column("status", guide_generation_job_status, nullable=False),
        sa.Column("asset_status", asset_status, nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_guide_generation_jobs_itinerary_version_status",
        "guide_generation_jobs",
        ["itinerary_version_id", "status"],
    )

    op.create_table(
        "guide_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("itinerary_id", sa.String(length=36), sa.ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "itinerary_version_id",
            sa.String(length=36),
            sa.ForeignKey("itinerary_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", guide_session_status, nullable=False),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "qa_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("guide_session_id", sa.String(length=36), sa.ForeignKey("guide_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", qa_message_role, nullable=False),
        sa.Column("intent", sa.String(length=64), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("validation_status", qa_message_validation_status, nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_qa_messages_guide_session_created_at", "qa_messages", ["guide_session_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_qa_messages_guide_session_created_at", table_name="qa_messages")
    op.drop_table("qa_messages")
    op.drop_table("guide_sessions")
    op.drop_index("ix_guide_generation_jobs_itinerary_version_status", table_name="guide_generation_jobs")
    op.drop_table("guide_generation_jobs")
    op.drop_index("ix_itineraries_current_version_id", table_name="itineraries")
    op.drop_constraint("fk_itineraries_current_version_id", "itineraries", type_="foreignkey")
    op.drop_table("itinerary_versions")
    op.drop_table("itineraries")
    op.drop_table("questionnaire_submissions")

    bind = op.get_bind()
    qa_message_validation_status.drop(bind, checkfirst=True)
    qa_message_role.drop(bind, checkfirst=True)
    guide_session_status.drop(bind, checkfirst=True)
    asset_status.drop(bind, checkfirst=True)
    guide_generation_job_status.drop(bind, checkfirst=True)
    guide_generation_job_type.drop(bind, checkfirst=True)
    itinerary_version_status.drop(bind, checkfirst=True)
    itinerary_status.drop(bind, checkfirst=True)
    questionnaire_submission_status.drop(bind, checkfirst=True)
