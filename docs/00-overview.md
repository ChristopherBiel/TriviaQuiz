# Documentation overview

This documentation is written for people who are new to Docker and VPS (Virtual Private Server) deployments. It explains the architecture first, then shows how to run the system locally and on a server. When you see “API,” it means Application Programming Interface. When you see “HTML” or “JSON,” think “web pages” and “data responses.”

## Why this page exists

This page is the starting map. It tells you what lives where, which docs to read first, and how to keep the docs accurate as the code evolves.

## Repository layout (what lives where)

- `app.py` starts the Flask app for local development on port 5600.
- `wsgi.py` is the Gunicorn entrypoint used in Docker.
- `backend/` contains all application logic: routes, services, storage adapters, and models.
- `templates/` contains the HTML pages (the user interface).
- `docker/` contains the Dockerfile, Docker Compose file, and Caddy config.
- `alembic/` and `alembic.ini` manage database migrations for Postgres.
- `scripts/` contains operational helpers like `scripts/ensure_admin.py`.
- `tests/` contains pytest-based tests.
- `docs/` contains architecture, runbooks, and interface documentation.

Common beginner mistake: treating `backend/` as optional. It is the core of the app, and almost everything you will change lives there.

## Documentation map

Why this exists: each page has a narrow job. You can jump directly to the topic you need.

- `docs/01-architecture.md` explains how requests flow and where data is stored.
- `docs/02-local-development.md` shows how to run the system with Docker on your laptop.
- `docs/03-deployment.md` walks through a simple VPS deployment with Caddy and HTTPS.
- `docs/04-operations.md` covers logs, health checks, and day-to-day operations.
- `docs/05-backups-and-restore.md` provides backup and restore runbooks.
- `docs/06-migrations.md` explains database migrations and Alembic.
- `docs/07-troubleshooting.md` lists common errors and fixes.
- `docs/08-environment-variables.md` lists every environment variable, exactly and explicitly.
- `docs/interfaces/storage.md` documents the storage interfaces and adapters.
- `docs/interfaces/services.md` documents the service layer boundaries.
- `docs/adr/` contains architecture decision records (ADRs).
- `backend/api/README.md` documents API endpoints.

## Recommended reading order

Why this exists: the order below builds understanding step-by-step for beginners.

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
- `docs/08-environment-variables.md`

## Docs verification checklist

Why this exists: docs can drift as the code changes. These checks keep them honest.

- [ ] Quickstart commands in `README.md` match `docker/docker-compose.yml`.
- [ ] Environment variable names match `docs/08-environment-variables.md` and `backend/core/settings.py`.
- [ ] The app still listens on port 5600 internally.
- [ ] The `/health` endpoint returns 200 and `{"status":"ok"}`.
- [ ] Migrations in `alembic/versions/` match the storage models.
- [ ] Storage adapter behavior in `backend/storage/` matches `docs/interfaces/storage.md`.
- [ ] Caddy proxy config in `docker/Caddyfile` matches `docs/01-architecture.md`.
- [ ] Backup commands in `docs/05-backups-and-restore.md` still work.
