"""add slug column to events

Revision ID: 0009_add_event_slug
Revises: 0008_add_media_text
Create Date: 2026-04-10
"""
from alembic import op
import sqlalchemy as sa
import secrets
import string

revision = "0009_add_event_slug"
down_revision = "0008_add_media_text"
branch_labels = None
depends_on = None

_SLUG_ALPHABET = string.ascii_letters + string.digits


def _generate_slug(length=8):
    return "".join(secrets.choice(_SLUG_ALPHABET) for _ in range(length))


def upgrade():
    op.add_column("events", sa.Column("slug", sa.String(), nullable=True))

    # Backfill existing events with unique slugs
    conn = op.get_bind()
    events = conn.execute(sa.text("SELECT event_id FROM events WHERE slug IS NULL")).fetchall()
    for (event_id,) in events:
        slug = _generate_slug()
        conn.execute(
            sa.text("UPDATE events SET slug = :slug WHERE event_id = :eid"),
            {"slug": slug, "eid": event_id},
        )

    op.create_unique_constraint("uq_events_slug", "events", ["slug"])
    op.create_index("ix_events_slug", "events", ["slug"], unique=True)


def downgrade():
    op.drop_index("ix_events_slug", table_name="events")
    op.drop_constraint("uq_events_slug", "events", type_="unique")
    op.drop_column("events", "slug")
