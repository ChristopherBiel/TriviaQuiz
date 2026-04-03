"""add media_text column to questions

Revision ID: 0008_add_media_text
Revises: 0007_add_live_session_tables
Create Date: 2026-04-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_add_media_text"
down_revision = "0007_add_live_session_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("media_text", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("questions", "media_text")
