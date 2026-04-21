# ADR 0002: Caddy as Reverse Proxy and TLS

**Status:** Superseded — Caddy was removed from docker-compose. The reverse proxy is now configured separately on the host, outside of the application's Docker stack.

## Context
The deployment needs HTTPS, automatic certificate management, and reverse proxying to the app container on port 5600.

## Original decision
Use Caddy as the reverse proxy and TLS endpoint within the Docker Compose stack.

## Current state
The Caddy service and Caddyfile have been removed from the repository. The reverse proxy (Caddy, nginx, or other) is expected to be set up separately on the host, forwarding to the app container on port 5600.

## Alternatives considered
- Nginx with Certbot.
- Traefik with Docker labels.
- Managed TLS termination at a cloud load balancer.
