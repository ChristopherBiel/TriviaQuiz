# Troubleshooting

## Common issues
- Caddy returns 502 or the app health check fails.
  - Check app logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f app`.
  - Ensure migrations ran: `docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head`.
  - Confirm Postgres and MinIO containers are healthy.
- Browser cannot reach the site.
  - Verify ports 80 and 443 are open on the host and not in use.
  - Confirm `CADDY_DOMAIN` resolves to the VPS IP.
- `relation "questions" does not exist` in logs.
  - Run Alembic migrations or set `POSTGRES_AUTO_CREATE=1` for local testing.
- Media files fail to load.
  - Confirm `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, and `MINIO_BUCKET` are correct.
  - If using `MEDIA_PROXY=1`, verify `/media/<key>` returns 200.
  - If using `MEDIA_PROXY=0`, ensure MinIO can generate presigned URLs and is reachable.
- Login returns `Email verification required` or `Admin approval required`.
  - Use `scripts/ensure_admin.py` to create or promote an admin user.
- Changes to `.env` do not apply.
  - Restart the stack: `docker compose -f docker/docker-compose.yml --env-file .env up -d`.

## Quick diagnostics
- Container status: `docker compose -f docker/docker-compose.yml --env-file .env ps`
- App health: `curl http://localhost/health`
- App logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f app`
