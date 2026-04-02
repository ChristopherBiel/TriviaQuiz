"""add live session tables for presenter mode

Revision ID: 0007_add_live_session_tables
Revises: 0006_add_event_is_published
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_add_live_session_tables"
down_revision = "0006_add_event_is_published"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "live_sessions",
        sa.Column("session_id", sa.String(), primary_key=True),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("join_code", sa.String(), nullable=False),
        sa.Column("current_question_index", sa.Integer(), nullable=False, server_default=sa.text("-1")),
        sa.Column("revealed_indices", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("locked_indices", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("show_questions_on_devices", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(), nullable=False, server_default="lobby"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_live_sessions_join_code", "live_sessions", ["join_code"])
    op.create_index("ix_live_sessions_status", "live_sessions", ["status"])

    op.create_table(
        "live_participants",
        sa.Column("participant_id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_live_participants_session_id", "live_participants", ["session_id"])

    op.create_table(
        "live_answers",
        sa.Column("answer_id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("participant_id", sa.String(), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("points_awarded", sa.Float(), nullable=True),
        sa.Column("max_points", sa.Float(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_live_answers_session_question", "live_answers", ["session_id", "question_index"])
    op.create_index(
        "uq_live_answers_session_participant_question",
        "live_answers",
        ["session_id", "participant_id", "question_index"],
        unique=True,
    )


def downgrade():
    op.drop_table("live_answers")
    op.drop_table("live_participants")
    op.drop_table("live_sessions")
