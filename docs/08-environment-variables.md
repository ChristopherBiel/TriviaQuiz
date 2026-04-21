# Environment variables

Defined in `.env` at the repo root (created from `docker/app.env.example`). The app reads `.env` via `python-dotenv` (`backend/core/settings.py`). For VPS deployments, keep `.env` on the server and do not commit it.

**Sensitivity labels:** `secret` = must be protected; `internal` = keep private but not a credential; `public` = safe to share.

## Application

| Variable | Default | Sensitivity | Notes |
|----------|---------|-------------|-------|
| `SECRET_KEY` | `change-me` | secret | Flask session signing. Must be unique in production. |
| `UPLOAD_FOLDER` | `static/uploads` | internal | Temporary upload staging before MinIO |
| `ALLOWED_EXTENSIONS` | `png,jpg,jpeg,gif,mp3,mp4` | public | Accepted media extensions |

## Email (SMTP)

| Variable | Default | Sensitivity | Notes |
|----------|---------|-------------|-------|
| `SMTP_ENABLED` | `0` | internal | Set to `1` to send real emails. When `0`, emails are printed to stdout. |
| `SMTP_HOST` | _(empty)_ | internal | SMTP server hostname (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | `587` | internal | SMTP server port (587 for STARTTLS, 465 for SSL) |
| `SMTP_USER` | _(empty)_ | secret | SMTP authentication username |
| `SMTP_PASSWORD` | _(empty)_ | secret | SMTP authentication password |
| `SMTP_FROM` | _(empty)_ | internal | Sender email address for outgoing mail |
| `SMTP_USE_TLS` | `1` | internal | `1` = STARTTLS (port 587); `0` = SSL (port 465) |
| `APP_BASE_URL` | `http://localhost:5600` | internal | Base URL for links in emails (verification, password reset) |

## Storage backend selection

| Variable | Default | Sensitivity | Notes |
|----------|---------|-------------|-------|
| `STORE_BACKEND` | `postgres` | internal | Default backend for all stores (`postgres` or `aws`) |
| `QUESTION_STORE` | `postgres` | internal | Override for question store |
| `USER_STORE` | `postgres` | internal | Override for user store |
| `MEDIA_STORE` | `minio` | internal | Override for media store |

## Media

| Variable | Default | Sensitivity | Notes |
|----------|---------|-------------|-------|
| `MEDIA_PROXY` | `1` | internal | `1` = serve media via `/media/*`; `0` = presigned MinIO URLs |
| `MEDIA_URL_EXPIRES_SECONDS` | `3600` | internal | Presigned URL TTL when `MEDIA_PROXY=0` |

## Postgres

| Variable | Default | Sensitivity | Notes |
|----------|---------|-------------|-------|
| `POSTGRES_DSN` | _(empty)_ | secret | Full connection string; overrides host/port/user/db when set |
| `POSTGRES_HOST` | `postgres` | internal | |
| `POSTGRES_PORT` | `5432` | internal | |
| `POSTGRES_DB` | `trivia` | internal | |
| `POSTGRES_USER` | `trivia` | secret | |
| `POSTGRES_PASSWORD` | `trivia` | secret | |
| `POSTGRES_AUTO_CREATE` | `0` (Compose) / `True` (code) | internal | Dev shortcut only — does not create migration files |

## MinIO

| Variable | Default | Sensitivity | Notes |
|----------|---------|-------------|-------|
| `MINIO_ENDPOINT` | `http://minio:9000` | internal | |
| `MINIO_ACCESS_KEY` | `minioadmin` (code) / `trivia` (Compose) | secret | Also used as `MINIO_ROOT_USER` inside the container |
| `MINIO_SECRET_KEY` | `minioadmin` (code) / `trivia-secret` (Compose) | secret | Also used as `MINIO_ROOT_PASSWORD` inside the container |
| `MINIO_BUCKET` | `trivia-media` | internal | |
| `MINIO_REGION` | `us-east-1` | internal | Used for S3 request signing |
| `MINIO_SECURE` | `0` | internal | Set to `1` to use HTTPS for the MinIO connection |
| `MINIO_AUTO_CREATE_BUCKET` | `1` | internal | Creates bucket on startup if missing |

## LLM evaluation

| Variable | Default | Sensitivity | Notes |
|----------|---------|-------------|-------|
| `LLM_EVAL_ENABLED` | `0` | internal | Set to `1` to enable LLM-assisted answer evaluation in event replay |
| `LLM_EVAL_API_KEY` | _(empty)_ | secret | API key for the LLM provider (Anthropic) |
| `LLM_EVAL_MODEL` | `claude-haiku-4-5-20251001` | internal | Model used for answer evaluation |
| `LLM_GEN_MODEL` | value of `LLM_EVAL_MODEL` | internal | Model used for content generation |

## Legacy AWS adapters

Only relevant when `STORE_BACKEND=aws`. These adapters use DynamoDB and S3 and are kept for migration tooling.

| Variable | Default | Sensitivity | Notes |
|----------|---------|-------------|-------|
| `AWS_REGION` | `eu-central-1` | internal | |
| `AWS_ENDPOINT_URL` | _(empty)_ | internal | Optional override (e.g. LocalStack) |
| `DYNAMODB_TABLE` | `TriviaQuestions` | internal | |
| `USERS_TABLE` | `TriviaUsersDev` | internal | |
| `AWS_S3_BUCKET` | `chris-trivia-media-bucket` | internal | |
| `AWS_ACCESS_KEY_ID` | _(empty)_ | secret | |
| `AWS_SECRET_ACCESS_KEY` | _(empty)_ | secret | |
| `AWS_SESSION_TOKEN` | _(empty)_ | secret | Optional |
| `AWS_PROFILE` | _(empty)_ | internal | Optional shared credentials profile |
