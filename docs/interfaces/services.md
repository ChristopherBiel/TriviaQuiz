# Service layer

Services live in `backend/services/` and own all business logic, authorization, and orchestration. Routes delegate to services; services call storage. Neither layer crosses the other's boundary.

## Question service (`backend/services/question_service.py`)

| Function | Signature | Notes |
|----------|-----------|-------|
| `get_question_by_id` | `(question_id) -> QuestionModel \| None` | |
| `get_all_questions` | `(filters, limit, offset, page_token, include_token)` | Returns `(questions, next_token)` |
| `create_question` | `(data) -> QuestionModel` | Normalizes tags/language; sets defaults |
| `update_question` | `(question_id, updates, user, role)` | `question_topic` is immutable after creation |
| `delete_question` | `(question_id) -> bool` | Also deletes associated media |
| `get_random_question_filtered` | `(seen_ids, filters) -> QuestionModel \| None` | Excludes already-seen IDs |
| `get_question_metadata` | `(filters) -> dict` | Topic/tag/language counts |

Pagination: `page_token` is a base64-encoded `last_key` dict. Internally, Postgres uses offset pagination.

## User service (`backend/services/user_service.py`)

| Function | Signature | Notes |
|----------|-----------|-------|
| `create_user` | `(data, acting_role)` | Hashes password; validates role |
| `get_user` | `(username) -> UserModel \| None` | |
| `list_users` | `(filters) -> list[UserModel]` | |
| `update_user` | `(username, updates, acting_role, acting_username)` | Enforces admin vs self-service boundaries |
| `delete_user` | `(username, acting_role)` | Admin only |
| `issue_verification` | `(user)` | Issues an email verification token |
| `verify_user` | `(token)` | Marks user as verified |
| `issue_reset_token` | `(user)` | Issues a password reset token |
| `reset_password` | `(token, new_password)` | Validates token, updates password hash |

## Adding a feature

1. Add a Pydantic model in `backend/models/`.
2. Extend abstract interfaces in `backend/storage/base.py`.
3. Implement in `backend/storage/postgres.py`.
4. Add service methods in `backend/services/`.
5. Add routes in `backend/api/` and templates in `templates/` if needed.
6. Generate and apply an Alembic migration.
