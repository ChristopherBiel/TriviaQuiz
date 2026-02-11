# Migrations
Database migrations are scripted changes to the database schema. They let you change tables in a safe, repeatable way.

## Why this exists
If the code and database schema are out of sync, the app will fail. Migrations keep them aligned.

## How migrations work here
Why this exists: knowing where migrations are configured helps you debug connection and schema issues.

- Alembic reads the SQLAlchemy metadata from `backend/storage/postgres.py`.
- The configuration is in `alembic/env.py` and `alembic.ini`.
- Migration files live in `alembic/versions/`.

## Run migrations (Docker)
Why this exists: this is the safest path when you run the app via Docker Compose.

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
```
What this does: runs Alembic inside the app container and applies all pending migrations.

## Run migrations (local Python)
Why this exists: this path is useful when running the app without Docker.

```bash
alembic upgrade head
```
What this does: runs Alembic on your machine using the same environment variables.

## Create a new migration
Why this exists: you will need this when you add or change database fields.

1. Update SQLAlchemy models in `backend/storage/postgres.py`.
2. Generate a migration.
   ```bash
   alembic revision --autogenerate -m "describe change"
   ```
   What this does: creates a new migration file by comparing models with the database.
3. Review the generated file in `alembic/versions/`.
4. Apply it.
   ```bash
   alembic upgrade head
   ```

## Auto-create tables (development only)
Why this exists: it is a shortcut for quick experiments.

- `POSTGRES_AUTO_CREATE=1` calls `Base.metadata.create_all()` on app startup.
- This does not create proper migrations, so do not use it for production.

Common beginner mistake: relying on auto-create in production and losing the ability to track schema changes.
