# ADR 0006: Backup Strategy (pg_dump + MinIO mirror + off-host)

## Context
The stack runs on a single VPS with Postgres and MinIO. Data loss risk must be mitigated with reliable backups that can be restored quickly.

## Decision
Use `pg_dump` for Postgres, MinIO mirroring for object storage, and copy backups off-host regularly.

## Consequences
- Backups can be automated via cron or a CI runner.
- Restores require disciplined runbooks and periodic restore drills.
- The approach favors simplicity over high-availability replication.

## Alternatives considered
- Postgres streaming replication and hot standby.
- Cloud-managed backups or snapshots.
- Full volume snapshots without logical dumps.
