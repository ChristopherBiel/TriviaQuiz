"""create core tables

Revision ID: 0001_create_core_tables
Revises: 
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_create_core_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "questions",
        sa.Column("question_id", sa.String(), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("added_by", sa.String(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.Column("question_topic", sa.String()),
        sa.Column("question_source", sa.String()),
        sa.Column("answer_source", sa.String()),
        sa.Column(
            "incorrect_answers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("times_asked", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("times_correct", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("times_incorrect", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "update_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("last_updated_at", sa.DateTime(), nullable=False),
        sa.Column("language", sa.String()),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("review_status", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("media_path", sa.String()),
    )
    op.create_index("ix_questions_topic_id", "questions", ["question_topic", "question_id"], unique=False)
    op.create_index("ix_questions_review_status", "questions", ["review_status"], unique=False)
    op.create_index("ix_questions_language", "questions", ["language"], unique=False)

    op.create_table(
        "users",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default=sa.text("'user'")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_token", sa.String()),
        sa.Column("verification_expires_at", sa.DateTime()),
        sa.Column("reset_token", sa.String()),
        sa.Column("reset_expires_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime()),
        sa.Column("last_login_ip", sa.String()),
    )


def downgrade():
    op.drop_table("users")
    op.drop_index("ix_questions_language", table_name="questions")
    op.drop_index("ix_questions_review_status", table_name="questions")
    op.drop_index("ix_questions_topic_id", table_name="questions")
    op.drop_table("questions")
