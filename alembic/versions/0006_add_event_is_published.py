"""add is_published column to events

Revision ID: 0006_add_event_is_published
Revises: 0005_add_email_verification_fields
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_add_event_is_published"
down_revision = "0005_add_email_verification_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "events",
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade():
    op.drop_column("events", "is_published")
