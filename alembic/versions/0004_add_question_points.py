"""add points column to questions

Revision ID: 0004_add_question_points
Revises: 0003_add_event_language
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_add_question_points"
down_revision = "0003_add_event_language"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("points", sa.Integer(), nullable=False, server_default=sa.text("1")))


def downgrade():
    op.drop_column("questions", "points")
