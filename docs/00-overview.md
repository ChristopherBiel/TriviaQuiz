# Documentation overview
TriviaQuiz is a Flask web app with an HTML UI and JSON APIs for gameplay, moderation, and admin workflows. The current deployment target is a single VPS with Docker Compose, using Caddy as the reverse proxy/TLS layer, Postgres for data, and MinIO for media.

## Repository layout
- `app.py` starts the Flask app for local development on port 5600.
- `wsgi.py` is the Gunicorn entrypoint used in Docker.
- `backend/` contains Flask blueprints, services, storage adapters, and models.
- `templates/` holds the HTML UI.
- `docker/` contains `Dockerfile`, `docker-compose.yml`, and Caddy config.
- `alembic/` and `alembic.ini` manage Postgres migrations.
- `scripts/` includes operational helpers like `scripts/ensure_admin.py`.
- `tests/` contains pytest-based tests.
- `docs/` contains architecture, runbooks, and interfaces.

## Documentation map
- `docs/01-architecture.md` explains the runtime layout and trust boundaries.
- `docs/02-local-development.md` covers Docker-based local setup.
- `docs/03-deployment.md` walks through VPS deployment with Caddy.
- `docs/04-operations.md` covers logs, health checks, and daily ops.
- `docs/05-backups-and-restore.md` provides backup/restore runbooks.
- `docs/06-migrations.md` documents Alembic workflows and schema updates.
- `docs/07-troubleshooting.md` lists common issues and fixes.
- `docs/interfaces/storage.md` documents storage interfaces and adapters.
- `docs/interfaces/services.md` documents service layer boundaries.
- `docs/adr/` contains architecture decision records.

## Recommended reading order
- `docs/00-overview.md`
- `docs/01-architecture.md`
- `docs/02-local-development.md`
- `docs/interfaces/storage.md`
- `docs/interfaces/services.md`
- `docs/03-deployment.md`
- `docs/04-operations.md`
- `docs/05-backups-and-restore.md`
- `docs/06-migrations.md`
- `docs/07-troubleshooting.md`

## Docs verification checklist
- [ ] Quickstart commands in `README.md` match `docker/docker-compose.yml`.
- [ ] Environment variable names match `backend/core/settings.py`.
- [ ] The app still listens on port 5600 internally.
- [ ] The `/health` endpoint is present and returns 200.
- [ ] Migrations in `alembic/versions/` match the storage models.
- [ ] Storage adapter behavior in `backend/storage/` matches interface docs.
- [ ] Caddy proxy config in `docker/Caddyfile` matches the architecture diagram.
- [ ] Backup commands still work against current Docker services.
