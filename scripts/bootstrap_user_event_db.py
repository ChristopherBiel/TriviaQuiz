#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys


TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize user and event storage in Postgres, then ensure one admin account exists."
        )
    )
    parser.add_argument(
        "--event-table",
        default=os.getenv("EVENTS_TABLE", "events"),
        help="Name of the event table to create (default: events)",
    )
    parser.add_argument(
        "--admin-username",
        default=os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin"),
        help="Admin username to create or update",
    )
    parser.add_argument(
        "--admin-email",
        default=os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com"),
        help="Admin email to create or update",
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("BOOTSTRAP_ADMIN_PASSWORD"),
        help="Admin password to set (required unless --skip-admin is used)",
    )
    parser.add_argument(
        "--skip-admin",
        action="store_true",
        help="Create tables only; do not create/update the admin user",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended actions without writing to the database",
    )
    args = parser.parse_args()

    if not TABLE_NAME_RE.match(args.event_table):
        parser.error("--event-table must match [A-Za-z_][A-Za-z0-9_]*")
    if not args.skip_admin and not args.admin_password:
        parser.error("--admin-password is required unless --skip-admin is set")

    return args


def _ensure_core_tables(dry_run: bool) -> None:
    if dry_run:
        print("Would ensure core SQLAlchemy tables (questions, users).")
        return
    from backend.storage.postgres import Base, get_engine

    Base.metadata.create_all(bind=get_engine())
    print("Ensured core SQLAlchemy tables (questions, users).")


def _ensure_event_table(event_table: str, dry_run: bool) -> None:
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {event_table} (
        event_id VARCHAR PRIMARY KEY,
        event_name VARCHAR NOT NULL,
        event_type VARCHAR NOT NULL DEFAULT 'replay',
        payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    );
    """

    create_type_idx_sql = f"""
    CREATE INDEX IF NOT EXISTS ix_{event_table}_event_type
    ON {event_table} (event_type);
    """

    create_created_idx_sql = f"""
    CREATE INDEX IF NOT EXISTS ix_{event_table}_created_at
    ON {event_table} (created_at DESC);
    """

    if dry_run:
        print(f"Would ensure event table '{event_table}' and indexes.")
        return

    from sqlalchemy import text
    from backend.storage.postgres import get_engine

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(create_table_sql))
        conn.execute(text(create_type_idx_sql))
        conn.execute(text(create_created_idx_sql))
    print(f"Ensured event table '{event_table}' and indexes.")


def _ensure_admin_user(username: str, email: str, password: str, dry_run: bool) -> bool:
    if dry_run:
        print(
            f"Would ensure admin user '{username}' (email='{email}', "
            "role=admin, is_verified=true, is_approved=true)."
        )
        return True

    from backend.services.user_service import create_user, get_user, update_user

    existing = get_user(username)
    if existing:
        updated = update_user(
            username,
            {"role": "admin", "is_verified": True, "is_approved": True, "password": password},
            acting_role="admin",
            acting_username=username,
        )
        ok = bool(updated)
    else:
        created = create_user(
            {
                "username": username,
                "email": email,
                "password": password,
                "role": "admin",
                "is_verified": True,
                "is_approved": True,
            },
            acting_role="admin",
        )
        ok = created is not None

    if ok:
        print(f"Ensured admin user '{username}' with admin, verified, and approved flags.")
    return ok


def main() -> int:
    args = _parse_args()

    _ensure_core_tables(dry_run=args.dry_run)
    _ensure_event_table(event_table=args.event_table, dry_run=args.dry_run)

    if args.skip_admin:
        print("Skipped admin user setup (--skip-admin).")
        return 0

    if _ensure_admin_user(
        username=args.admin_username,
        email=args.admin_email,
        password=args.admin_password,
        dry_run=args.dry_run,
    ):
        return 0

    print("Failed to create or update admin user.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
