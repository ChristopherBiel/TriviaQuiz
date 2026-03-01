# Backups and restore

## Postgres backup

```bash
set -a; source .env; set +a

mkdir -p backups/pg
docker compose -f docker/docker-compose.yml --env-file .env exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c \
  > backups/pg/trivia.dump
```

The `-T` flag disables TTY allocation, which is required for output redirection.

## Postgres restore

```bash
set -a; source .env; set +a

docker compose -f docker/docker-compose.yml --env-file .env cp \
  backups/pg/trivia.dump postgres:/tmp/trivia.dump

docker compose -f docker/docker-compose.yml --env-file .env exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/trivia.dump
```

## MinIO backup

MinIO is only reachable inside the Docker network; use a temporary `mc` container on the same network.

```bash
set -a; source .env; set +a

mkdir -p backups/minio
docker run --rm --network docker_default \
  -e MINIO_ACCESS_KEY -e MINIO_SECRET_KEY -e MINIO_BUCKET \
  -v "$PWD/backups/minio:/backup" \
  minio/mc sh -lc \
  'mc alias set local http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" && \
   mc mirror --overwrite "local/$MINIO_BUCKET" "/backup/$MINIO_BUCKET"'
```

The default Compose network name is `docker_default`. Adjust if you changed the project name.

## MinIO restore

```bash
set -a; source .env; set +a

docker run --rm --network docker_default \
  -e MINIO_ACCESS_KEY -e MINIO_SECRET_KEY -e MINIO_BUCKET \
  -v "$PWD/backups/minio:/backup" \
  minio/mc sh -lc \
  'mc alias set local http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" && \
   mc mirror --overwrite "/backup/$MINIO_BUCKET" "local/$MINIO_BUCKET"'
```

## Off-host copies

Copy `backups/pg/` and `backups/minio/` to a second host or object store. Keep at least two generations.

## Restore drill

1. Restore Postgres from the latest dump.
2. Mirror the MinIO bucket from backup.
3. `docker compose -f docker/docker-compose.yml --env-file .env up -d`
4. Confirm `GET /health` returns 200 and that question data and media load.
