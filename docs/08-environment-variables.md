# Environment variables (full specification)

This page lists every environment variable used by the application or the Docker Compose setup. It is intentionally explicit so new contributors do not need to guess which variables matter.

## How to read this
- **Required** means the app or deployment is not safe to run without setting it.
- **Default** is what the code or `docker/docker-compose.yml` uses if you do nothing.
- **Example** is a safe placeholder value.
- **Sensitivity** uses three labels: `public config` (safe to share), `internal` (should stay private but is not a credential), and `secret` (must be protected like a password or key).

## Where to define variables
- For Docker Compose runs, define variables in `.env` at the repo root. This is the file created by `cp docker/app.env.example .env`.
- For local Python runs (without Docker), set the same variables in your shell or in a local `.env` file. `backend/core/settings.py` loads `.env` via `python-dotenv`.
- For VPS deployments, keep `.env` on the server and do not commit it.

## Application and Docker Compose variables

| Variable | Required | Default | Example | Used by | Controls | Sensitivity | Where defined |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SECRET_KEY` | Yes (production) | `change-me` (Compose) / `default_secret_key` (code) | `change-me` | app | Flask session cookie signing | secret | `.env` |
| `UPLOAD_FOLDER` | No | `static/uploads` | `static/uploads` | app | Temporary upload location before storage | internal | `.env` |
| `ALLOWED_EXTENSIONS` | No | `png,jpg,jpeg,gif,mp3,mp4` | `png,jpg,jpeg,gif,mp3,mp4` | app | Allowed media file extensions | public config | `.env` |
| `STORE_BACKEND` | No | `postgres` | `postgres` | app | Default storage backend for questions/users/media | internal | `.env` |
| `QUESTION_STORE` | No | `postgres` | `postgres` | app | Override for question store backend | internal | `.env` |
| `USER_STORE` | No | `postgres` | `postgres` | app | Override for user store backend | internal | `.env` |
| `MEDIA_STORE` | No | `minio` | `minio` | app | Override for media store backend | internal | `.env` |
| `MEDIA_PROXY` | No | `1` | `1` | app | When `1`, serve media via `/media/*` endpoint | internal | `.env` |
| `MEDIA_URL_EXPIRES_SECONDS` | No | `3600` | `3600` | app | Presigned URL time-to-live (seconds) when `MEDIA_PROXY=0` | internal | `.env` |
| `POSTGRES_DSN` | No | empty | `(empty)` | app, migrations | Full database connection string (overrides host/port/user/db) | secret | `.env` |
| `POSTGRES_HOST` | No | `postgres` | `postgres` | app, migrations | Database host | internal | `.env` |
| `POSTGRES_PORT` | No | `5432` | `5432` | app, migrations | Database port | internal | `.env` |
| `POSTGRES_DB` | No | `trivia` | `trivia` | app, postgres, migrations | Database name | internal | `.env` |
| `POSTGRES_USER` | No | `trivia` | `trivia` | app, postgres, migrations | Database username | secret | `.env` |
| `POSTGRES_PASSWORD` | No | `trivia` | `trivia` | app, postgres, migrations | Database password | secret | `.env` |
| `POSTGRES_AUTO_CREATE` | No | `0` (Compose) / `True` (code) | `0` | app | Auto-create tables on startup (dev only) | internal | `.env` |
| `MINIO_ENDPOINT` | No | `http://minio:9000` | `http://minio:9000` | app | S3-compatible endpoint URL | internal | `.env` |
| `MINIO_ACCESS_KEY` | No | `trivia` (Compose) / `minioadmin` (code) | `trivia` | app, minio | Access key for MinIO (also used as `MINIO_ROOT_USER` inside container) | secret | `.env` |
| `MINIO_SECRET_KEY` | No | `trivia-secret` (Compose) / `minioadmin` (code) | `trivia-secret` | app, minio | Secret key for MinIO (also used as `MINIO_ROOT_PASSWORD` inside container) | secret | `.env` |
| `MINIO_BUCKET` | No | `trivia-media` | `trivia-media` | app | Bucket name for media objects | internal | `.env` |
| `MINIO_REGION` | No | `us-east-1` | `us-east-1` | app | S3 region value used for signing | internal | `.env` |
| `MINIO_SECURE` | No | `0` | `0` | app | Use HTTPS when connecting to MinIO | internal | `.env` |
| `MINIO_AUTO_CREATE_BUCKET` | No | `1` | `1` | app | Create bucket on startup if missing | internal | `.env` |
| `AWS_REGION` | No | `eu-central-1` | `eu-central-1` | app (legacy) | AWS region for DynamoDB/S3 adapters | internal | `.env` |
| `AWS_ENDPOINT_URL` | No | empty | `(empty)` | app (legacy) | Optional AWS endpoint override (LocalStack) | internal | `.env` |
| `DYNAMODB_TABLE` | No | `TriviaQuestions` | `TriviaQuestions` | app (legacy) | DynamoDB questions table name | internal | `.env` |
| `USERS_TABLE` | No | `TriviaUsersDev` | `TriviaUsersDev` | app (legacy) | DynamoDB users table name | internal | `.env` |
| `AWS_S3_BUCKET` | No | `chris-trivia-media-bucket` | `chris-trivia-media-bucket` | app (legacy) | S3 bucket for media | internal | `.env` |
| `AWS_ACCESS_KEY_ID` | No | empty | `(empty)` | app (legacy) | AWS access key for DynamoDB/S3 adapters | secret | `.env` |
| `AWS_SECRET_ACCESS_KEY` | No | empty | `(empty)` | app (legacy) | AWS secret key for DynamoDB/S3 adapters | secret | `.env` |
| `AWS_SESSION_TOKEN` | No | empty | `(empty)` | app (legacy) | Optional AWS session token | secret | `.env` |
| `AWS_PROFILE` | No | empty | `(empty)` | app (legacy) | Optional AWS profile name for shared credentials | internal | `.env` |
| `CADDY_DOMAIN` | Yes (production) | `localhost` | `localhost` | caddy | Public domain name for HTTPS and routing | public config | `.env` |
| `CADDY_EMAIL` | Yes (production) | empty | `(empty)` | caddy | Email for HTTPS certificate registration | public config | `.env` |

## Notes for beginners
- `POSTGRES_DSN` is optional. If it is set, the app ignores `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.
- `STORE_BACKEND` defaults to `postgres`, which is the new non-AWS path. Only set `STORE_BACKEND=aws` if you are intentionally using the legacy DynamoDB/S3 adapters.
- If you use AWS adapters, you must also provide AWS credentials via `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (and optionally `AWS_SESSION_TOKEN` or `AWS_PROFILE`).
- `CADDY_DOMAIN` and `CADDY_EMAIL` are only required when you want real HTTPS certificates. For local development, leaving `CADDY_DOMAIN=localhost` is fine.

Example AWS block (only if you intentionally use the AWS adapters):
```bash
AWS_REGION=eu-central-1
AWS_ACCESS_KEY_ID=AKIAEXAMPLE
AWS_SECRET_ACCESS_KEY=change-me
AWS_SESSION_TOKEN=
AWS_PROFILE=
DYNAMODB_TABLE=TriviaQuestions
USERS_TABLE=TriviaUsersDev
AWS_S3_BUCKET=chris-trivia-media-bucket
```

## Files that must match this list
- `docker/app.env.example` is the canonical example for `.env` and matches this document exactly.
