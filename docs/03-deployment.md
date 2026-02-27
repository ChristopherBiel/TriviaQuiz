# Deployment (VPS)

## Prerequisites

- VPS with Docker Engine and the Compose plugin
- DNS A/AAAA record pointing to the VPS IP
- Ports 80 and 443 open on the firewall
- A production `.env` (see `docs/08-environment-variables.md`)

## Initial deployment

```bash
git clone <repo> && cd <repo>
cp docker/app.env.example .env
# Edit .env — set SECRET_KEY, CADDY_DOMAIN, CADDY_EMAIL, and database/MinIO credentials
docker compose -f docker/docker-compose.yml --env-file .env up -d
docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
```

Caddy provisions a TLS certificate automatically once DNS resolves. Visit `https://<CADDY_DOMAIN>`.

## Updates

```bash
git pull
docker compose -f docker/docker-compose.yml --env-file .env build
docker compose -f docker/docker-compose.yml --env-file .env up -d
docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
```

## Operational commands

```bash
# Start / recreate containers
docker compose -f docker/docker-compose.yml --env-file .env up -d

# Stop without deleting volumes
docker compose -f docker/docker-compose.yml --env-file .env stop

# Stream app logs
docker compose -f docker/docker-compose.yml --env-file .env logs -f app
```

## Notes

- Keep `POSTGRES_AUTO_CREATE=0` in production — use Alembic migrations.
- Postgres and MinIO must stay private to the Docker network.
- `SECRET_KEY` must be a unique random value; the default `change-me` is not safe for production.
