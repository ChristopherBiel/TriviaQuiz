## Backend overview
Flask application built via `backend.main.create_app`, split into blueprints for HTML pages (`backend.routes`, `backend.auth`) and JSON APIs (`backend.api.*`). Business logic lives in services, with DynamoDB/S3 adapters in `backend/db` and Pydantic models in `backend/models`.

### Modules at a glance
- `routes.py` – HTML-facing endpoints for gameplay, moderation UI, and user management.
- `auth.py` – signup/login/logout plus approval and verification gate checks (session-based).
- `api/` – JSON APIs for questions, users, and question detail pages (see `backend/api/README.md`).
- `services/` – orchestrates validation, ownership checks, media lifecycle, and permission rules.
- `db/` – DynamoDB adapters for questions/users and S3 helpers for media (config via env vars).
- `models/` – Pydantic models (e.g., `QuestionModel`, `UserModel`) with sanitization and defaults.
- `utils/` – password hashing, simple email stub, and shared validation helpers.
- `core/config.py` – Flask settings (secret key, upload folder, allowed extensions).

### Environment
Exports are read by multiple layers:
- `SECRET_KEY` – required for Flask sessions.
- `AWS_REGION` – AWS region (default `eu-central-1`).
- `DYNAMODB_TABLE` – questions table name.
- `USERS_TABLE` – users table name.
- `AWS_S3_BUCKET` – bucket for media uploads.

### Running just the backend
From repo root:
```bash
python app.py  # starts create_app() on 0.0.0.0:5600
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

### Media handling
- Upload via `media` form field; allowed extensions: `jpg,jpeg,png,gif,mp3,mp4`.
- New uploads go to `AWS_S3_BUCKET`; updates clean up previous objects when replaced or removed.

### Testing
Run `pytest` (unit + integration under `tests/api`, `tests/services`). Provide AWS env vars and disposable DynamoDB/S3 resources when running anything that touches the adapters.
