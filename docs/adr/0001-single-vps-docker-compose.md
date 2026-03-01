# ADR 0001: Single VPS + Docker Compose

## Context
The project is moving away from AWS-managed services and needs a simple, cost-effective deployment target. The app consists of a Flask service, Postgres, MinIO, and a reverse proxy.

## Decision
Deploy the stack on a single VPS using Docker Compose (`docker/docker-compose.yml`).

## Consequences
- Operations are simple and predictable with a single host and a single compose file.
- Scaling is limited to vertical scaling or manual multi-host changes.
- Availability depends on one VPS, so backups and restore drills are critical.

## Alternatives considered
- Kubernetes or Swarm for multi-host orchestration.
- Managed PaaS offerings (Heroku, Render, Fly.io).
- Separate hosts for database and object storage.
