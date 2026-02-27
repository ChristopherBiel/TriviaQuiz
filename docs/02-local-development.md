# Local development

Requires Docker Engine with the Compose plugin.

## Setup

```bash
cp docker/app.env.example .env
docker compose -f docker/docker-compose.yml --env-file .env up -d
docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
```

Visit `http://localhost` (Caddy) or check `http://localhost/health` for `{"status":"ok"}`.

Optionally create an admin user:
```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm app \
  python scripts/ensure_admin.py --username admin --email admin@example.com --password "change-me"
```

## Notes

- The app listens on port 5600 inside Docker; access it through Caddy at `http://localhost`.
- `POSTGRES_AUTO_CREATE=1` auto-creates tables on startup but does not generate migration files — use Alembic instead.
- `MEDIA_PROXY=1` (default) routes media requests through the app at `/media/<key>`.
- `.env` changes require a container restart to take effect.

## Common commands

```bash
# Container status
docker compose -f docker/docker-compose.yml --env-file .env ps

# Stream app logs
docker compose -f docker/docker-compose.yml --env-file .env logs -f app

# Stop without deleting volumes
docker compose -f docker/docker-compose.yml --env-file .env stop

# Remove containers (volumes are preserved)
docker compose -f docker/docker-compose.yml --env-file .env down
```

## Running tests

```bash
pytest                                           # all tests
pytest tests/api/question_api_test.py            # single file
```
