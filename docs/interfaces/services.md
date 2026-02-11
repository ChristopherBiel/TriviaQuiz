# Service layer interfaces

## Overview
Service modules live in `backend/services/` and encapsulate business rules, authorization checks, and data orchestration. Routes handle HTTP concerns and delegate to services.

## Question service (`backend/services/question_service.py`)
Responsibilities:
- Validation and normalization of question data.
- Enforcing invariants like immutable `question_topic`.
- Pagination token encoding/decoding.
- Media lifecycle (upload, replace, delete) through `MediaStore`.
- Filtering and random selection for gameplay.

Key functions:
- `get_question_by_id(question_id)`
- `get_all_questions(filters, limit, offset, page_token, include_token)`
- `create_question(data)`
- `update_question(question_id, updates, user, role)`
- `delete_question(question_id)`
- `get_random_question_filtered(seen_ids, filters)`
- `get_question_metadata(filters)`

Usage example:
```python
from backend.services.question_service import create_question

question = create_question({
    "question": "Capital of France?",
    "answer": "Paris",
    "added_by": "admin",
    "tags": ["geography"],
})
```

## User service (`backend/services/user_service.py`)
Responsibilities:
- User creation with password hashing and role validation.
- Admin-only field updates and deletes.
- Issuing verification and reset tokens.
- Enforcing admin vs self-service boundaries.

Key functions:
- `create_user(data, acting_role)`
- `get_user(username)`
- `list_users(filters)`
- `update_user(username, updates, acting_role, acting_username)`
- `delete_user(username, acting_role)`
- `issue_verification(user)` / `verify_user(token)`
- `issue_reset_token(user)` / `reset_password(token, new_password)`

## Route vs service vs storage boundaries
- Routes in `backend/api/` and `backend/routes.py` handle HTTP parsing, session checks, and response shaping.
- Services enforce business rules and orchestration.
- Storage adapters in `backend/storage/` handle persistence and are backend-agnostic behind interfaces.

## Adding a new feature/table (pattern)
1. Add a Pydantic model in `backend/models/`.
2. Extend storage interfaces in `backend/storage/base.py` if needed.
3. Implement adapters in `backend/storage/postgres.py` (and optional AWS adapters).
4. Add service methods in `backend/services/` for business logic.
5. Add API routes in `backend/api/` and templates in `templates/` if needed.
6. Create an Alembic migration in `alembic/versions/` and run `alembic upgrade head`.
