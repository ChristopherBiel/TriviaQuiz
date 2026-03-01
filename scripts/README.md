## Operational scripts

### `ensure_admin.py`
Create or promote an admin user with verified/approved flags set to `True`. Useful for seeding a fresh environment or recovering access when no admin exists.

Prereqs:
- AWS credentials with write access to the users table (`USERS_TABLE` env, default `TriviaUsersDev`)
- Standard app env vars (`AWS_REGION`, `SECRET_KEY` optional for this script)

Usage:
```bash
python scripts/ensure_admin.py \
  --username admin \
  --email admin@example.com \
  --password "super-secret"
```

The script is idempotent: if the user exists, it updates role/verification/approval and password; otherwise it creates the account.

### `bootstrap_user_event_db.py`
Initialize Postgres-backed user/event storage and seed one admin account.

What it does:
- Ensures core SQLAlchemy tables exist (`questions`, `users`)
- Creates an `events` table (configurable via `--event-table`) with indexes
- Creates or updates one admin user with `role=admin`, `is_verified=True`, and `is_approved=True`

Prereqs:
- Postgres connection env vars (`POSTGRES_*` or `POSTGRES_DSN`)
- App dependencies installed (`pip install -r requirements.txt`)

Usage:
```bash
python scripts/bootstrap_user_event_db.py \
  --admin-username admin \
  --admin-email admin@example.com \
  --admin-password "change-me"
```

Optional dry-run:
```bash
python scripts/bootstrap_user_event_db.py \
  --admin-username admin \
  --admin-email admin@example.com \
  --admin-password "change-me" \
  --dry-run
```

### `migrate_aws_questions_media.py`
Migrate legacy question records from AWS DynamoDB and copy their media from source S3 into the currently configured target stores.

What it does:
- Scans source DynamoDB questions table
- Loads each row into `QuestionModel` and writes to target `QuestionStore`
- Copies each referenced media object from source S3 to target `MediaStore`
- Rewrites each question `media_path` to the new target media path

Prereqs:
- Source AWS credentials/profile with read access to DynamoDB and S3
- Target app storage configured via env vars (`QUESTION_STORE`, `MEDIA_STORE`, etc.)
- App dependencies installed (`pip install -r requirements.txt`)

Usage:
```bash
python scripts/migrate_aws_questions_media.py \
  --source-region eu-central-1 \
  --source-dynamodb-table TriviaQuestions \
  --source-s3-bucket chris-trivia-media-bucket
```

Useful flags:
- `--replace-existing` overwrite target questions with matching IDs
- `--allow-missing-media` keep migrating if media transfer fails (drops `media_path`)
- `--dry-run` simulate the migration without writing
- `--limit N` process only the first `N` source records
