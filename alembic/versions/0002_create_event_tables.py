"""create event tables and rename question_source

Revision ID: 0002_create_event_tables
Revises: 0001_create_core_tables
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_create_event_tables"
down_revision = "0001_create_core_tables"
branch_labels = None
depends_on = None


def upgrade():
    # --- New table: events ---
    op.create_table(
        "events",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("team_score", sa.Float(), nullable=True),
        sa.Column("best_score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "question_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_events_name", "events", ["name"], unique=False)
    op.create_index("ix_events_created_by", "events", ["created_by"], unique=False)

    # --- New table: event_replays ---
    op.create_table(
        "event_replays",
        sa.Column("replay_id", sa.String(), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(),
            sa.ForeignKey("events.event_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column(
            "answers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_replays_event_score",
        "event_replays",
        ["event_id", sa.text("score DESC")],
        unique=False,
    )

    # --- Alter questions table: rename question_source → event_id, add source_note ---
    # First migrate existing free-text values to source_note
    op.add_column("questions", sa.Column("source_note", sa.String(), nullable=True))
    op.execute("UPDATE questions SET source_note = question_source WHERE question_source IS NOT NULL")
    op.execute("UPDATE questions SET question_source = NULL")
    # Now rename the column
    op.alter_column("questions", "question_source", new_column_name="event_id")
    op.create_index("ix_questions_event_id", "questions", ["event_id"], unique=False)


def downgrade():
    # Reverse questions changes
    op.drop_index("ix_questions_event_id", table_name="questions")
    op.alter_column("questions", "event_id", new_column_name="question_source")
    op.execute("UPDATE questions SET question_source = source_note WHERE source_note IS NOT NULL AND question_source IS NULL")
    op.drop_column("questions", "source_note")

    # Drop event_replays
    op.drop_index("ix_replays_event_score", table_name="event_replays")
    op.drop_table("event_replays")

    # Drop events
    op.drop_index("ix_events_created_by", table_name="events")
    op.drop_index("ix_events_name", table_name="events")
    op.drop_table("events")
