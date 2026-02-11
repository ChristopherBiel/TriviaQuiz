# Backups and restore

## Postgres backups (pg_dump)
1. Export environment variables from `.env`.
   ```bash
   set -a
   source .env
   set +a
   ```
2. Create a backup directory and dump the database.
   ```bash
   mkdir -p backups/pg
   docker compose -f docker/docker-compose.yml --env-file .env exec -T postgres \
     pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c \
     > backups/pg/trivia.dump
   ```

## Postgres restore (pg_restore)
1. Copy the dump into the Postgres container.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env cp \
     backups/pg/trivia.dump postgres:/tmp/trivia.dump
   ```
2. Restore into the target database.
   ```bash
   set -a
   source .env
   set +a
   docker compose -f docker/docker-compose.yml --env-file .env exec -T postgres \
     pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/trivia.dump
   ```

## MinIO mirroring (bucket backup)
MinIO is only exposed inside the Docker network by default, so run the MinIO client on the same network. The default compose project name is `docker` when using `-f docker/docker-compose.yml`, which creates the network `docker_default`. If you set a different project name, adjust the network accordingly.

1. Export environment variables from `.env`.
   ```bash
   set -a
   source .env
   set +a
   ```
2. Mirror the bucket to a local backup directory using the MinIO client container.
   ```bash
   mkdir -p backups/minio
   docker run --rm --network docker_default \
     -e MINIO_ACCESS_KEY -e MINIO_SECRET_KEY -e MINIO_BUCKET \
     -v "$PWD/backups/minio:/backup" \
     minio/mc sh -lc 'mc alias set local http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" && mc mirror --overwrite "local/$MINIO_BUCKET" "/backup/$MINIO_BUCKET"'
   ```

## MinIO restore (bucket restore)
1. Export environment variables from `.env`.
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

## Off-host copies
- Copy `backups/pg/` and `backups/minio/` to a second host or storage provider (for example, via `scp` or `rsync`).
- Verify the remote copy and keep at least two generations of backups.

## Restore drill (verification steps)
1. Restore Postgres from the most recent dump.
2. Mirror the MinIO bucket from backup.
3. Restart the stack: `docker compose -f docker/docker-compose.yml --env-file .env up -d`.
4. Confirm `GET /health` returns 200 and that question data and media load in the UI.
