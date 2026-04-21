# Service layer

Services live in `backend/services/` and own all business logic, authorization, and orchestration. Routes delegate to services; services call storage. Neither layer crosses the other's boundary.

## Question service (`backend/services/question_service.py`)

| Function | Signature | Notes |
|----------|-----------|-------|
| `get_question_by_id` | `(question_id) -> QuestionModel \| None` | |
| `get_all_questions` | `(filters, limit, offset, page_token, include_token)` | Returns `(questions, next_token)` |
| `create_question` | `(data) -> QuestionModel` | Normalizes tags/language; sets defaults |
| `update_question` | `(question_id, updates, user, role)` | `question_topic` is immutable after creation |
| `delete_question` | `(question_id, confirm=False) -> dict` | Returns `{success, linked_event_id?}`; rejects if linked to event unless `confirm=True` |
| `count_questions` | `(filters) -> int` | Total count matching filters |
| `get_random_question_filtered` | `(seen_ids, filters) -> QuestionModel \| None` | Excludes already-seen IDs |
| `get_question_metadata` | `(filters) -> dict` | Topic/tag/language counts |

Pagination: `page_token` is a base64-encoded `last_key` dict. Internally, Postgres uses offset pagination.

## User service (`backend/services/user_service.py`)

| Function | Signature | Notes |
|----------|-----------|-------|
| `create_user` | `(data, acting_role)` | Hashes password; validates role; rejects duplicate email |
| `get_user` | `(username) -> UserModel \| None` | |
| `get_user_by_email` | `(email) -> UserModel \| None` | |
| `list_users` | `(filters) -> list[UserModel]` | |
| `update_user` | `(username, updates, acting_role, acting_username)` | Enforces admin vs self-service boundaries |
| `delete_user` | `(username, acting_role)` | Admin only |
| `issue_verification` | `(user, ttl_minutes=15)` | Issues a verification token + 6-digit code |
| `verify_user` | `(token_or_code)` | Accepts token or code; marks user verified + approved; applies pending email change |
| `issue_reset_token` | `(user, ttl_minutes=15)` | Issues a reset token + 6-digit code |
| `reset_password` | `(token_or_code, new_password)` | Accepts token or code; validates expiry, updates password hash |
| `issue_email_change` | `(user, new_email, ttl_minutes=15)` | Stores pending email; issues verification token + code |

## Event service (`backend/services/event_service.py`)

| Function | Signature | Notes |
|----------|-----------|-------|
| `create_event` | `(data, username) -> EventModel \| None` | |
| `get_event` | `(event_id_or_slug) -> EventModel \| None` | Accepts ID or slug |
| `list_events` | `(filters, limit, offset) -> (list, int)` | Returns `(events, total_count)` |
| `update_event` | `(event_id, updates, username, role)` | Creator or admin only |
| `delete_event` | `(event_id, username, role, delete_questions)` | Optionally deletes linked questions |
| `add_question_to_event` | `(event_id, question_id) -> bool` | |
| `remove_question_from_event` | `(event_id, question_id) -> bool` | |
| `reorder_event_questions` | `(event_id, question_ids) -> bool` | |
| `get_event_questions` | `(event_id) -> list` | Ordered list of questions |

## Replay service (`backend/services/replay_service.py`)

| Function | Signature | Notes |
|----------|-----------|-------|
| `start_replay` | `(event_id) -> dict \| None` | Returns questions without answers |
| `evaluate_replay` | `(event_id, user_answers) -> dict \| None` | Scores answers; uses LLM when enabled |
| `submit_replay` | `(event_id, user_answers, ...)` | Persists a scored replay attempt |
| `get_leaderboard` | `(event_id, limit=10) -> list[dict]` | |
| `has_played_event` | `(event_id, user_id) -> bool` | |
| `get_replay_detail` | `(replay_id) -> dict \| None` | |
| `delete_replay` | `(replay_id, event_id) -> bool` | |

## Live service (`backend/services/live_service.py`)

| Function | Signature | Notes |
|----------|-----------|-------|
| `create_live_session` | `(event_id, username, ...) -> LiveSessionModel \| None` | Generates a join code |
| `get_live_session` | `(session_id) -> LiveSessionModel \| None` | |
| `advance_question` | `(session_id, username) -> LiveSessionModel \| None` | Move to next question |
| `lock_question` | `(session_id, question_index, username) -> LiveSessionModel \| None` | Stop accepting answers |
| `reveal_question` | `(session_id, question_index, username) -> dict \| None` | Reveal answer and auto-score |
| `finish_session` | `(session_id, username) -> LiveSessionModel \| None` | Mark session complete |
| `join_session` | `(join_code, display_name, user_id?) -> LiveParticipantModel \| None` | |
| `submit_answer` | `(session_id, participant_id, question_index, answer_text) -> LiveAnswerModel \| None` | |
| `get_session_state` | `(session_id, participant_id?, is_presenter?) -> dict \| None` | Tailored view per role |

## Adding a feature

1. Add a Pydantic model in `backend/models/`.
2. Extend abstract interfaces in `backend/storage/base.py`.
3. Implement in `backend/storage/postgres.py`.
4. Add service methods in `backend/services/`.
5. Add routes in `backend/api/` and templates in `templates/` if needed.
6. Generate and apply an Alembic migration.
