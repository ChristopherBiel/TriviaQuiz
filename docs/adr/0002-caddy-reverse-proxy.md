# ADR 0002: Caddy as Reverse Proxy and TLS

## Context
The deployment needs HTTPS, automatic certificate management, and reverse proxying to the app container on port 5600.

## Decision
Use Caddy as the reverse proxy and TLS endpoint (`docker/Caddyfile`).

## Consequences
- Automatic HTTPS with minimal configuration.
- Simplified proxy configuration and upgrades.
- Requires ports 80 and 443 open on the VPS.

## Alternatives considered
- Nginx with Certbot.
- Traefik with Docker labels.
- Managed TLS termination at a cloud load balancer.
