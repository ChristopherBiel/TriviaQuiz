![Deployment to EC2](https://github.com/ChristopherBiel/TriviaQuiz/actions/workflows/deploy.yml/badge.svg)

# TriviaQuiz
Flask-powered trivia game with session-based authentication, DynamoDB for questions/users, and S3-backed media uploads. Serves a lightweight HTML UI plus JSON APIs that power moderation, gameplay, and admin workflows.

## Repository layout
- `app.py` – Flask entrypoint binding everything together
- `backend/` – application code (Flask blueprints, services, models, data access)
- `templates/` – HTML pages for gameplay, auth, moderation, and question detail
- `scripts/` – operational helpers (e.g., ensuring an admin account)
- `docker/` – Dockerfile for containerized deployments
- `tests/` – API/service integration tests (pytest)
- `requirements.txt` – Python dependencies

## Features
- Auth + approval: signup/login with email verification flags and admin approval gates
- Question workflow: CRUD APIs, random unseen selection with filters, review/approval toggles
- Media support: upload images/audio/video to S3 and store URLs alongside questions
- Admin tools: user management, question moderation, database view via HTML pages
- Pagination: token + offset based listing for DynamoDB-backed questions

## Prerequisites
- Python 3.12+
- AWS credentials configured (DynamoDB + S3 access)
- DynamoDB tables:
  - Questions: partition key `id` (optionally a sort key `question_topic` if you need topic-level uniqueness)
  - Users: partition key `user_id`
- S3 bucket for media uploads (public-read or presigned access depending on your policy)

## Quickstart (local)
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
pip install -r requirements.txt

export AWS_REGION=eu-central-1
export DYNAMODB_TABLE=TriviaQuestions
export USERS_TABLE=TriviaUsersDev
export AWS_S3_BUCKET=your-media-bucket
export SECRET_KEY=replace-me

python app.py  # serves on http://127.0.0.1:5600
```

Sessions are cookie-based; ensure `SECRET_KEY` is set in production. The app expects AWS credentials through the standard SDK sources (env vars, AWS profile, or instance roles).

## Environment variables
- `AWS_REGION` (default `eu-central-1`) – AWS region for DynamoDB/S3
- `DYNAMODB_TABLE` – DynamoDB table for questions
- `USERS_TABLE` – DynamoDB table for users
- `AWS_S3_BUCKET` – bucket for media uploads
- `SECRET_KEY` – Flask session key (required for auth)
- Optional: standard AWS SDK vars (`AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.)

## Running with Docker
```bash
docker build -t triviaquiz -f docker/Dockerfile .
docker run --rm -p 5600:5600 \
  -e AWS_REGION=eu-central-1 \
  -e DYNAMODB_TABLE=TriviaQuestions \
  -e USERS_TABLE=TriviaUsersDev \
  -e AWS_S3_BUCKET=your-media-bucket \
  -e SECRET_KEY=replace-me \
  triviaquiz
```
Grant the container IAM access via env vars or the host/role you run with.

## Testing
```bash
pytest
```
Most tests mock AWS calls, but integration tests still expect AWS environment variables to be present. Provide disposable tables/bucket when running against real services.

## API and data model docs
- Question/user API usage: `backend/api/README.md`
- DynamoDB/S3 expectations and pagination details: `backend/db/README.md`
- Backend architecture overview: `backend/README.md`

## Operational helpers
- `scripts/ensure_admin.py` – create or promote an admin user with verified/approved flags. Example:
  ```bash
  python scripts/ensure_admin.py --username admin --email you@example.com --password "secret"
  ```
