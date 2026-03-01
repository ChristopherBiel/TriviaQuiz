# ADR 0003: Postgres Replacing DynamoDB

## Context
The previous architecture depended on DynamoDB and AWS credentials. The new deployment target is a single VPS and must avoid AWS-specific infrastructure.

## Decision
Adopt Postgres as the primary data store, implemented via SQLAlchemy and managed with Alembic migrations (`backend/storage/postgres.py`, `alembic/`).

## Consequences
- Schema changes require migrations (`alembic upgrade head`).
- The application owns database operations and backups.
- Querying and filtering are simpler and more expressive than DynamoDB scans.

## Alternatives considered
- Continue using DynamoDB with AWS credentials.
- Use SQLite for production (not suitable for multi-user workloads).
- Use a managed Postgres service instead of self-hosting.
