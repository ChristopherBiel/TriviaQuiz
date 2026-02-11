# Migrations

## Overview
Postgres schema management is handled by Alembic. Alembic uses the SQLAlchemy metadata from `backend/storage/postgres.py` via `alembic/env.py`.

## Run migrations (Docker)
```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
```

## Run migrations (local Python)
```bash
alembic upgrade head
```
This requires the same environment variables used by the app (`POSTGRES_*` or `POSTGRES_DSN`).

## Create a new migration
1. Update SQLAlchemy models in `backend/storage/postgres.py`.
2. Generate a migration.
   ```bash
   alembic revision --autogenerate -m "describe change"
   ```
3. Review the generated file in `alembic/versions/` and apply it.
   ```bash
   alembic upgrade head
   ```

## Auto-create tables (development only)
- `POSTGRES_AUTO_CREATE=1` calls `Base.metadata.create_all()` on app startup.
- This is useful for quick local testing but does not replace Alembic in production.
