# Storage interfaces

Abstract interfaces are defined in `backend/storage/base.py`. The factory (`backend/storage/factory.py`) selects implementations via `get_question_store()`, `get_user_store()`, `get_media_store()` — all `lru_cache`d, controlled by `STORE_BACKEND` / `QUESTION_STORE` / `USER_STORE` / `MEDIA_STORE` env vars.

## QuestionStore

Implementations: `PostgresQuestionStore` (`postgres.py`), `DynamoQuestionStore` (`aws.py`, legacy).

| Method | Return | Notes |
|--------|--------|-------|
| `add(question: QuestionModel)` | `bool` | `False` on conflict |
| `get_by_id(question_id: str)` | `QuestionModel \| None` | |
| `list(filters, limit, last_key)` | `(list[QuestionModel], last_key \| None)` | `last_key` is `{"offset": int}` for Postgres, `LastEvaluatedKey` for DynamoDB |
| `list_by_topic(topic, limit, last_key)` | same as `list` | Convenience wrapper |
| `update(question_id, updates)` | `QuestionModel \| None` | `None` if not found |
| `delete(question_id)` | `bool` | `False` if not found |

## UserStore

Implementations: `PostgresUserStore` (`postgres.py`), `DynamoUserStore` (`aws.py`, legacy).

| Method | Return | Notes |
|--------|--------|-------|
| `add(user: UserModel)` | `bool` | `False` on conflict |
| `get_by_username(username)` | `UserModel \| None` | |
| `get_by_id(user_id)` | `UserModel \| None` | |
| `get_by_email(email)` | `UserModel \| None` | |
| `get_by_verification_token(token)` | `UserModel \| None` | Base has O(n) fallback; Postgres overrides with indexed query |
| `get_by_verification_code(code)` | `UserModel \| None` | Base has O(n) fallback; Postgres overrides with indexed query |
| `get_by_reset_token(token)` | `UserModel \| None` | Base has O(n) fallback; Postgres overrides with indexed query |
| `get_by_reset_code(code)` | `UserModel \| None` | Base has O(n) fallback; Postgres overrides with indexed query |
| `list(filters)` | `list[UserModel]` | |
| `update(user_id, updates)` | `UserModel \| None` | |
| `delete(user_id)` | `bool` | |

## MediaStore

Implementations: `MinioMediaStore` (`minio.py`), `S3MediaStore` (`aws.py`, legacy).

| Method | Return | Notes |
|--------|--------|-------|
| `upload(file)` | `str \| None` | Returns object key; `None` on rejection |
| `delete(media_path)` | `bool` | `False` on missing key or error |
| `get_url(media_path, expires_in)` | `str \| None` | `/media/<key>` when `MEDIA_PROXY=1`; presigned URL when `MEDIA_PROXY=0` |
| `download(media_path)` | `(IO[bytes], content_type, content_length)` | Used by `GET /media/<key>` |

## Data invariants

- `question_id` is a UUID set by `QuestionModel` if not provided.
- `question_topic` defaults to `"General"` and is immutable after creation (enforced in `question_service.update_question`).
- `tags` and `language` are normalized to lowercase by `QuestionModel` validators.
- `review_status` defaults to `False`; gameplay and metadata endpoints filter to reviewed questions only.

## Usage

```python
from backend.storage.factory import get_question_store

store = get_question_store()
question = store.get_by_id("some-uuid")
```
