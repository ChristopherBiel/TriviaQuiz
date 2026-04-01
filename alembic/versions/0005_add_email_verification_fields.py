"""add verification_code, reset_code, pending_email columns and email unique constraint

Revision ID: 0005_add_email_verification_fields
Revises: 0004_add_question_points
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_add_email_verification_fields"
down_revision = "0004_add_question_points"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("verification_code", sa.String(), nullable=True))
    op.add_column("users", sa.Column("reset_code", sa.String(), nullable=True))
    op.add_column("users", sa.Column("pending_email", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade():
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "pending_email")
    op.drop_column("users", "reset_code")
    op.drop_column("users", "verification_code")
