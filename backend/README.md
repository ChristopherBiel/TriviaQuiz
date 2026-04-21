## Backend overview
Flask application built via `backend.main.create_app`, split into blueprints for HTML pages (`backend.routes`, `backend.auth`) and JSON APIs (`backend.api.*`). Business logic lives in services, with storage adapters in `backend/storage` and Pydantic models in `backend/models`.

### Modules at a glance
- `routes.py` – HTML page routes, login status, and admin user actions.
- `auth.py` – signup/login/logout plus approval and verification gate checks (session-based).
- `api/` – JSON APIs for questions, users, events, live sessions, and media (see `backend/api/README.md`).
- `services/` – orchestrates validation, ownership checks, media lifecycle, and permission rules.
- `storage/` – abstract storage interfaces (`base.py`) and implementations (`postgres.py`, `minio.py`, `aws.py` legacy).
- `db/` – legacy wrapper functions that delegate to the service/storage layer.
- `models/` – Pydantic models (e.g., `QuestionModel`, `UserModel`, `EventModel`, `LiveSessionModel`) with sanitization and defaults.
- `utils/` – password hashing and a simple email stub.
- `core/settings.py` – Pydantic Settings configuration, reads `.env` via python-dotenv.
- `core/config.py` – Flask settings derived from `core/settings.py`.

### Environment
All configuration via environment variables. See `docs/08-environment-variables.md` for the full reference. Key variables:
- `SECRET_KEY` – required for Flask sessions.
- `STORE_BACKEND` – storage backend (`postgres` or `aws`, default: `postgres`).
- `POSTGRES_*` – database connection settings.
- `MINIO_*` – object storage settings.
- `MEDIA_PROXY` – `1` to proxy media through Flask, `0` for presigned URLs.

### Running just the backend
From repo root:
```bash
python app.py  # starts create_app() on 0.0.0.0:5600
```
For production or Docker:
```bash
gunicorn --bind 0.0.0.0:5600 wsgi:app
```
or import in tests:
```python
from backend.main import create_app
app = create_app()
client = app.test_client()
```

### Auth and permissions
- Sessions are cookie-based. `/signup` issues verification tokens via `utils.email_stub.send_email` and `/login` requires verified + approved users.
- Question creation/update requires authentication; deletes require admin; user CRUD APIs are admin-only.
Admin user management is handled via the `/users` API routes (used by `templates/approve_user.html`).

### Gameplay endpoints
The main UI now uses `/questions/random` and `/questions/metadata` for gameplay and filters.
Legacy question routes on `backend.routes` have been removed.

### Media handling
- Upload via `media` form field; allowed extensions: `jpg,jpeg,png,gif,mp3,mp4`.
- New uploads go to MinIO (or S3 when using the legacy AWS adapter); updates clean up previous objects when replaced or removed.

### Testing
Run `pytest` (unit + integration under `tests/api`, `tests/services`). CI runs against a real PostgreSQL 16 instance.
