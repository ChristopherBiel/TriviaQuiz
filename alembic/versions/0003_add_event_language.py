"""add language column to events

Revision ID: 0003_add_event_language
Revises: 0002_create_event_tables
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_add_event_language"
down_revision = "0002_create_event_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("events", sa.Column("language", sa.String(), nullable=True))


def downgrade():
    op.drop_column("events", "language")
