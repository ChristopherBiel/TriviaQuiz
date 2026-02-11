# Operations

## Logs
- Tail app logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f app`
- Tail Postgres logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f postgres`
- Tail MinIO logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f minio`
- Tail Caddy logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f caddy`

## Health checks
- The app exposes `GET /health` and returns `{"status":"ok"}` on success.
- For local Docker, use `http://localhost/health`.
- The Docker healthcheck for the app uses the same endpoint.

## Secrets and configuration
- Application and infrastructure settings are loaded from environment variables.
- `backend/core/settings.py` loads `.env` via `python-dotenv` for local, non-Docker runs.
- Keep `.env` out of version control and rotate `SECRET_KEY` if it is exposed.

## Admin access
- If no admin exists or access is lost, create or promote one:
  ```bash
  docker compose -f docker/docker-compose.yml --env-file .env run --rm app \
    python scripts/ensure_admin.py --username admin --email admin@example.com --password "change-me"
  ```

## Media delivery
- With `MEDIA_PROXY=1`, media URLs are served through `/media/<object_key>`.
- With `MEDIA_PROXY=0`, media URLs are presigned by MinIO and served directly.
- MinIO credentials and bucket name come from `MINIO_*` environment variables.

## Runtime inspection
- View running containers: `docker compose -f docker/docker-compose.yml --env-file .env ps`
- Open a shell in the app container: `docker compose -f docker/docker-compose.yml --env-file .env exec app /bin/sh`
