# Storage interfaces

Abstract interfaces are defined in `backend/storage/base.py`. The factory (`backend/storage/factory.py`) selects implementations via `get_question_store()`, `get_user_store()`, `get_media_store()`, `get_event_store()`, `get_replay_store()`, `get_live_store()` — all `lru_cache`d, controlled by `STORE_BACKEND` / `QUESTION_STORE` / `USER_STORE` / `MEDIA_STORE` env vars.

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

## EventStore

Implementation: `PostgresEventStore` (`postgres.py`).

| Method | Return | Notes |
|--------|--------|-------|
| `add(event: EventModel)` | `bool` | |
| `get_by_id(event_id: str)` | `EventModel \| None` | |
| `get_by_slug(slug: str)` | `EventModel \| None` | |
| `list(filters, limit, offset)` | `(list[EventModel], int)` | Returns items and total count |
| `update(event_id, updates)` | `EventModel \| None` | |
| `delete(event_id)` | `bool` | |

## ReplayStore

Implementation: `PostgresReplayStore` (`postgres.py`).

| Method | Return | Notes |
|--------|--------|-------|
| `save(replay: ReplayAttemptModel)` | `bool` | |
| `get_by_id(replay_id)` | `ReplayAttemptModel \| None` | |
| `list_by_event(event_id, limit, offset)` | `list[ReplayAttemptModel]` | |
| `list_by_user(user_id)` | `list[ReplayAttemptModel]` | |
| `get_leaderboard(event_id, limit)` | `list[ReplayAttemptModel]` | Top scores |
| `has_user_played(event_id, user_id)` | `bool` | |
| `delete(replay_id)` | `bool` | |

## LiveStore

Implementation: `PostgresLiveStore` (`postgres.py`).

| Method | Return | Notes |
|--------|--------|-------|
| `create_session(session: LiveSessionModel)` | `bool` | |
| `get_session(session_id)` | `LiveSessionModel \| None` | |
| `get_session_by_code(join_code)` | `LiveSessionModel \| None` | |
| `update_session(session_id, updates)` | `LiveSessionModel \| None` | |
| `add_participant(participant: LiveParticipantModel)` | `bool` | |
| `get_participants(session_id)` | `list[LiveParticipantModel]` | |
| `get_participant(participant_id)` | `LiveParticipantModel \| None` | |
| `save_answer(answer: LiveAnswerModel)` | `bool` | |
| `get_answers(session_id, question_index?)` | `list[LiveAnswerModel]` | |
| `update_answer(answer_id, updates)` | `LiveAnswerModel \| None` | |

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
