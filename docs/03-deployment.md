# Deployment (VPS)

## Prerequisites
- A VPS with Docker Engine and the Docker Compose plugin installed.
- A domain name pointing to the VPS IP address (A/AAAA record).
- Ports 80 and 443 open on the VPS firewall.

## Deployment steps
1. SSH into the VPS and clone the repo.
2. Create an env file from the example and set production secrets.
   ```bash
   cp docker/app.env.example .env
   ```
3. Set Caddy domain settings in `.env`.
   - `CADDY_DOMAIN` should be your public domain (for example, `trivia.example.com`).
   - `CADDY_EMAIL` should be the email used for ACME certificates.
4. Start the stack.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env up -d
   ```
5. Run migrations.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
   ```
6. Visit `https://<your-domain>` once Caddy finishes provisioning TLS.

## Operational commands
- Start services: `docker compose -f docker/docker-compose.yml --env-file .env up -d`
- Stop services: `docker compose -f docker/docker-compose.yml --env-file .env stop`
- Restart services: `docker compose -f docker/docker-compose.yml --env-file .env restart`
- View logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f app`

## Updates
1. Pull the latest changes.
2. Rebuild and restart containers.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env build
   docker compose -f docker/docker-compose.yml --env-file .env up -d
   ```
3. Run migrations after code updates.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
   ```

## Deployment notes
- The Flask app listens on port 5600 internally; Caddy is the only public entrypoint.
- Keep `POSTGRES_AUTO_CREATE=0` in production and run Alembic migrations explicitly.
- MinIO and Postgres stay private to the Docker network unless you expose them intentionally.
