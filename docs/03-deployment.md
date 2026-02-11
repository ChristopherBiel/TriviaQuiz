# Deployment (VPS)
This guide deploys the full stack to a single VPS (Virtual Private Server), such as a Hetzner instance. It uses Docker Compose and Caddy for HTTPS.

## Why this exists
Deploying to a server can be intimidating. This page breaks it into small, safe steps and explains each one.

## Prerequisites
Why this exists: these are the minimum requirements before you start.

- A VPS with Docker Engine and the Docker Compose plugin installed.
- A domain name pointing to the VPS IP address (Domain Name System or DNS A/AAAA record).
- Ports 80 and 443 open on the VPS firewall.
- A `.env` file with production values. See `docs/08-environment-variables.md`.

Common beginner mistake: forgetting to open ports 80 and 443, which prevents HTTPS certificates from working.

## Deployment steps (step-by-step)
Why this exists: the exact steps below match the current Docker configuration.

A migration is a scripted database change. You apply migrations after code updates that change database structure.

1. SSH into the VPS and clone the repo.
2. Create an env file and edit it for production.
   ```bash
   cp docker/app.env.example .env
   ```
   What this does: creates the file Docker Compose reads for configuration.
3. Set Caddy values in `.env`. `CADDY_DOMAIN` should be your public domain (example: `trivia.example.com`) and `CADDY_EMAIL` should be your email for HTTPS certificate (TLS) registration.
4. Start the stack.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env up -d
   ```
   What this does: builds and starts all containers in the background.
5. Run migrations.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
   ```
   What this does: creates or updates Postgres tables to match the code.
6. Visit `https://<your-domain>` once Caddy finishes provisioning TLS.

Common beginner mistake: visiting the app before DNS changes have propagated. It can take a few minutes for DNS updates to go live.

## Operational commands
Why this exists: you will use these during updates and debugging.

- Start services: `docker compose -f docker/docker-compose.yml --env-file .env up -d`
  What this does: starts or recreates containers.
- Stop services: `docker compose -f docker/docker-compose.yml --env-file .env stop`
  What this does: stops containers without deleting volumes.
- Restart services: `docker compose -f docker/docker-compose.yml --env-file .env restart`
  What this does: restarts containers with the same configuration.
- View logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f app`
  What this does: streams app logs for debugging.

## Updates
Why this exists: deployments should be repeatable and safe.

1. Pull the latest changes.
2. Rebuild and restart containers.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env build
   docker compose -f docker/docker-compose.yml --env-file .env up -d
   ```
   What this does: rebuilds the image and restarts containers with new code.
3. Run migrations after code updates.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
   ```
   What this does: applies any schema changes required by the new code.

## Deployment notes
Why this exists: these are the most common sources of confusion.

- The Flask app listens on port 5600 internally; Caddy is the only public entrypoint.
- Keep `POSTGRES_AUTO_CREATE=0` in production and use Alembic migrations instead.
- MinIO and Postgres should remain private to the Docker network unless you intentionally expose them.
