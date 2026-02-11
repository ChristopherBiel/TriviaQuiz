# Backups and restore
This runbook covers Postgres data backups and MinIO object backups, plus how to restore them.

## Why this exists
A single VPS can fail. Backups are the only reliable way to recover data after mistakes or hardware loss.

## Key concepts (quick definitions)
- **Backup**: a copy of your data stored outside the running system.
- **Restore**: loading a backup back into the system.
- **Volume**: a Docker-managed disk area where Postgres and MinIO store data.

## Postgres backups (pg_dump)
Why this exists: `pg_dump` creates a portable snapshot of the database.

1. Export variables from `.env`.
   ```bash
   set -a
   source .env
   set +a
   ```
   What this does: makes `.env` values available to the shell.

2. Create a backup directory and dump the database.
   ```bash
   mkdir -p backups/pg
   docker compose -f docker/docker-compose.yml --env-file .env exec -T postgres \
     pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c \
     > backups/pg/trivia.dump
   ```
   What this does: runs `pg_dump` inside the Postgres container and writes the dump file locally.

Common beginner mistake: forgetting `-T` and getting a stuck terminal because `pg_dump` expects a terminal (TTY).

## Postgres restore (pg_restore)
Why this exists: this replays the dump back into a clean database.

1. Copy the dump into the Postgres container.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env cp \
     backups/pg/trivia.dump postgres:/tmp/trivia.dump
   ```
   What this does: places the dump file inside the container.

2. Restore into the target database.
   ```bash
   set -a
   source .env
   set +a
   docker compose -f docker/docker-compose.yml --env-file .env exec -T postgres \
     pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/trivia.dump
   ```
   What this does: drops existing objects and restores the dump.

## MinIO mirroring (bucket backup)
Why this exists: MinIO stores media objects that are not in Postgres.

MinIO is only exposed inside the Docker network, so we use a temporary MinIO client container on the same network.

1. Export variables from `.env`.
   ```bash
   set -a
   source .env
   set +a
   ```

2. Mirror the bucket to a local backup directory.
   ```bash
   mkdir -p backups/minio
   docker run --rm --network docker_default \
     -e MINIO_ACCESS_KEY -e MINIO_SECRET_KEY -e MINIO_BUCKET \
     -v "$PWD/backups/minio:/backup" \
     minio/mc sh -lc 'mc alias set local http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" && mc mirror --overwrite "local/$MINIO_BUCKET" "/backup/$MINIO_BUCKET"'
   ```
   What this does: connects to the MinIO container and copies the bucket to `backups/minio/`.

Common beginner mistake: using the wrong Docker network name. The default network for `docker/docker-compose.yml` is `docker_default`.

## MinIO restore (bucket restore)
Why this exists: restores media files back into MinIO.

1. Export variables from `.env`.
   ```bash
   set -a
   source .env
   set +a
   ```

2. Mirror the backup back into MinIO.
   ```bash
   docker run --rm --network docker_default \
     -e MINIO_ACCESS_KEY -e MINIO_SECRET_KEY -e MINIO_BUCKET \
     -v "$PWD/backups/minio:/backup" \
     minio/mc sh -lc 'mc alias set local http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" && mc mirror --overwrite "/backup/$MINIO_BUCKET" "local/$MINIO_BUCKET"'
   ```
   What this does: uploads files from the backup directory into the MinIO bucket.

## Off-host copies
Why this exists: backups stored only on the VPS can be lost with the VPS.

- Copy `backups/pg/` and `backups/minio/` to a second host or storage provider.
- Keep at least two generations of backups.

## Restore drill (verification steps)
Why this exists: a backup is only useful if you can restore it.

1. Restore Postgres from the most recent dump.
2. Mirror the MinIO bucket from backup.
3. Restart the stack: `docker compose -f docker/docker-compose.yml --env-file .env up -d`.
4. Confirm `GET /health` returns 200 and that question data and media load in the UI.
