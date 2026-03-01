# Migrations

Alembic manages the Postgres schema. Migration files live in `alembic/versions/`. Configuration is in `alembic/env.py` and `alembic.ini`; models are sourced from `backend/storage/postgres.py`.

## Apply migrations

```bash
# In Docker (preferred)
docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head

# Locally
alembic upgrade head
```

## Create a migration

1. Edit SQLAlchemy models in `backend/storage/postgres.py`.
2. Generate the migration file:
   ```bash
   alembic revision --autogenerate -m "describe change"
   ```
3. Review the generated file in `alembic/versions/` — autogenerate is not always complete.
4. Apply: `alembic upgrade head`

## Notes

- `POSTGRES_AUTO_CREATE=1` calls `Base.metadata.create_all()` on startup. It is a dev shortcut and does not produce migration files — do not use in production.
- Always run `alembic upgrade head` after deploying code that changes the schema.
