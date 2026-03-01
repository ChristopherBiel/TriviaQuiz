![Deployment to VPS](https://github.com/ChristopherBiel/TriviaQuiz/actions/workflows/deploy.yml/badge.svg)
![Version](https://img.shields.io/badge/dynamic/regex?url=https%3A%2F%2Fraw.githubusercontent.com%2FChristopherBiel%2FTriviaQuiz%2Fmain%2FVERSION&search=%5E(.%2B)%24&label=version&color=7c6aef)

# TriviaQuiz
TriviaQuiz is a Flask-powered trivia game with session-based authentication, HTML pages for gameplay/moderation, and JSON APIs for question and user workflows. The current architecture targets a single VPS deployment with Docker Compose, using Caddy, Postgres, and MinIO.

## Tech stack
- Python 3.12, Flask, Gunicorn
- Postgres 16 with SQLAlchemy and Alembic
- MinIO (S3-compatible) with boto3
- Caddy reverse proxy with automatic TLS
- Docker Compose for local/dev/prod orchestration

## Architecture at a glance
- Public traffic hits Caddy (ports 80/443) and is reverse-proxied to the app container on port 5600.
- The app container runs Gunicorn + Flask and calls the service layer and storage adapters.
- Postgres stores questions/users; MinIO stores media.
- `/media/*` is served by the app when `MEDIA_PROXY=1`.

## Quickstart (Docker, local)
1. Create a local env file.
   ```bash
   cp docker/app.env.example .env
   ```
2. Start the stack.
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env up -d
   ```
3. Run database migrations.

   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
   ```

4. (Optional) Create an admin user.

   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app \
     python scripts/ensure_admin.py --username admin --email admin@example.com --password "change-me"
   ```

5. (Optional) Bootstrap user/event storage and seed admin in one step.

   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app \
     python scripts/bootstrap_user_event_db.py \
       --admin-username admin --admin-email admin@example.com --admin-password "change-me"
   ```

6. (Optional) Migrate legacy questions/media from AWS DynamoDB + S3 into current stores.

   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm app \
     python scripts/migrate_aws_questions_media.py \
       --source-region eu-central-1 \
       --source-dynamodb-table TriviaQuestions \
       --source-s3-bucket chris-trivia-media-bucket
   ```
   
7. Open the app at `http://localhost` (Caddy) and check `http://localhost/health`.

## Key commands / workflows
- Build: `docker compose -f docker/docker-compose.yml --env-file .env build`
- Start: `docker compose -f docker/docker-compose.yml --env-file .env up -d`
- Stop: `docker compose -f docker/docker-compose.yml --env-file .env stop`
- Logs: `docker compose -f docker/docker-compose.yml --env-file .env logs -f app`
- Migrations: `docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head`
- Tests: `pytest` (install `pytest` in your environment if needed)
- Bootstrap user/event DB + admin: `python scripts/bootstrap_user_event_db.py --admin-username admin --admin-email admin@example.com --admin-password "change-me"`
- Migrate legacy AWS questions/media: `python scripts/migrate_aws_questions_media.py --source-region eu-central-1 --source-dynamodb-table TriviaQuestions --source-s3-bucket chris-trivia-media-bucket`

## Configuration overview
- Full list and definitions: `docs/08-environment-variables.md`
- App: `SECRET_KEY`, `STORE_BACKEND`, `QUESTION_STORE`, `USER_STORE`, `MEDIA_STORE`, `MEDIA_PROXY`, `MEDIA_URL_EXPIRES_SECONDS`, `UPLOAD_FOLDER`, `ALLOWED_EXTENSIONS`
- Postgres: `POSTGRES_DSN`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_AUTO_CREATE`
- MinIO: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_REGION`, `MINIO_SECURE`, `MINIO_AUTO_CREATE_BUCKET`
- Caddy: `CADDY_DOMAIN`, `CADDY_EMAIL`
- Legacy AWS adapters (optional): `AWS_REGION`, `AWS_ENDPOINT_URL`, `DYNAMODB_TABLE`, `USERS_TABLE`, `AWS_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_PROFILE`

## Docs
- Overview: `docs/00-overview.md`
- Architecture: `docs/01-architecture.md`
- Local development: `docs/02-local-development.md`
- Deployment: `docs/03-deployment.md`
- Operations: `docs/04-operations.md`
- Backups and restore: `docs/05-backups-and-restore.md`
- Migrations: `docs/06-migrations.md`
- Troubleshooting: `docs/07-troubleshooting.md`
- Environment variables: `docs/08-environment-variables.md`
- Interfaces: `docs/interfaces/storage.md`, `docs/interfaces/services.md`
- Architecture decisions: `docs/adr/`
- API reference: `backend/api/README.md`
