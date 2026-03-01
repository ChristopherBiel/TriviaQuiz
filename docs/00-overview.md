# Overview

## Repository layout

| Path | Purpose |
|------|---------|
| `app.py` | Local dev entry point (port 5600) |
| `wsgi.py` | Gunicorn entry point (Docker) |
| `backend/` | Application logic: routes, services, storage adapters, models |
| `templates/` | Jinja2 HTML templates |
| `docker/` | Dockerfile, docker-compose.yml, Caddyfile |
| `alembic/` | Database migration scripts |
| `scripts/` | Operational helpers (e.g. `ensure_admin.py`) |
| `tests/` | pytest test suite |
| `docs/` | Architecture docs and runbooks |

## Documentation map

| File | Topic |
|------|-------|
| `docs/01-architecture.md` | Request flow, layer boundaries, infrastructure |
| `docs/02-local-development.md` | Running the stack locally with Docker Compose |
| `docs/03-deployment.md` | VPS deployment |
| `docs/04-operations.md` | Logs, health checks, runtime inspection |
| `docs/05-backups-and-restore.md` | Backup and restore runbooks |
| `docs/06-migrations.md` | Alembic database migrations |
| `docs/07-troubleshooting.md` | Common failures and fixes |
| `docs/08-environment-variables.md` | All env vars with defaults and sensitivity |
| `docs/interfaces/storage.md` | Storage adapter interfaces and invariants |
| `docs/interfaces/services.md` | Service layer API and boundaries |
| `docs/adr/` | Architecture decision records |
| `backend/api/README.md` | HTTP endpoint reference |
