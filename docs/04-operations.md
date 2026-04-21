# Operations

## Health check

```bash
curl http://localhost:5600/health   # expects {"status":"ok"}
```

Docker uses the same endpoint to mark the container healthy.

## Logs

```bash
docker compose -f docker/docker-compose.yml --env-file .env logs -f app       # Flask/Gunicorn
docker compose -f docker/docker-compose.yml --env-file .env logs -f postgres  # DB errors
docker compose -f docker/docker-compose.yml --env-file .env logs -f minio     # Object storage
```

## Runtime inspection

```bash
# Container status and health
docker compose -f docker/docker-compose.yml --env-file .env ps

# Shell into the app container
docker compose -f docker/docker-compose.yml --env-file .env exec app /bin/sh
```

## Admin user

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm app \
  python scripts/ensure_admin.py --username admin --email admin@example.com --password "change-me"
```

## Media delivery

- `MEDIA_PROXY=1` (default): media served by the app at `/media/<key>`.
- `MEDIA_PROXY=0`: app returns presigned MinIO URLs; browser fetches from MinIO directly.

## Secrets

All configuration comes from environment variables. See `docs/08-environment-variables.md`. The app reads `.env` automatically; container restarts are required after changes.
