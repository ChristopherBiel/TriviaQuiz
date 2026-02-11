# Local development

## Prerequisites
- Docker Desktop (or Docker Engine) with the Docker Compose plugin.
- A shell that can run `docker compose` commands.

## Local setup (Docker Compose)
1. Create a local env file from the example.
   ```bash
   cp docker/app.env.example .env
   ```
2. Start the stack.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env up -d
   ```
3. Run database migrations.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
   ```
4. (Optional) Create an admin user for the UI.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app \
     python scripts/ensure_admin.py --username admin --email admin@example.com --password "change-me"
   ```
5. Open the app at `http://localhost` and verify `http://localhost/health` returns `{"status":"ok"}`.

## Notes for local runs
- The Flask app listens on port 5600 inside the Docker network and is served externally by Caddy.
- Postgres and MinIO are only reachable inside the Docker network by default.
- If you set `POSTGRES_AUTO_CREATE=1`, the app will create tables on startup. The default in Docker is `0`, so run Alembic migrations instead.
- Media URLs are proxied through the app when `MEDIA_PROXY=1` (default).

## Useful local commands
- View running services: `docker compose -f docker/docker-compose.yml --env-file .env ps`
- Tail app logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f app`
- Stop services: `docker compose -f docker/docker-compose.yml --env-file .env stop`
- Remove services: `docker compose -f docker/docker-compose.yml --env-file .env down`
