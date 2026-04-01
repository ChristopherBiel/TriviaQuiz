## TriviaQuiz API
Session-backed JSON endpoints served by Flask blueprints. Use the `/login` route from `backend/auth.py` to obtain a session cookie, then call these APIs.

### Conventions
- JSON responses with `{error: string}` on failure. Content negotiation: `GET /questions/<id>` will render `templates/question_detail.html` when HTML is preferred.
- Auth: POST/PUT/DELETE routes require a logged-in session; admin-only where noted.
- Pagination: `limit` (>=1) and `offset` (>=0) plus an opaque `page_token`/`next_page_token` derived from DynamoDB `LastEvaluatedKey`.
- Filters: `tags` (list or comma-separated), `language`, `question_topic`, `review_status` (`true/false`). Filtering happens before pagination.
- Media: upload as multipart form-data with `media` file; allowed extensions `jpg,jpeg,png,gif,mp4,mp3`. Set `remove_media=true` or `media_path=null` to delete media.

### Question endpoints (base `/questions`)
- `GET /questions/` — list questions with filters + pagination. Response: `{"items":[...],"pagination":{"limit":n,"offset":n,"count":n,"total":n,"next_page_token":str|null}}`.
- `GET /questions/<question_id>` — fetch a question; 404 if missing; renders HTML when `Accept` prefers text/html.
- `GET /questions/metadata` — fetch distinct `languages`, `topics`, and `tags` for reviewed questions.
- `POST /questions/` — create a question. Required: `question`, `answer`, `added_by`. Optional: `incorrect_answers`, `question_topic`, `event_id`, `source_note`, `answer_source`, `language`, `tags`, `review_status`, `media_path`. Auth required. If `question_topic` is omitted, it defaults to `General`. If `event_id` is provided, the question is automatically added to that event.
- `PUT /questions/<question_id>` — partial update. Auth required; only owner or admin can update. Accepts JSON or multipart with `media`. `question_topic` cannot be updated after creation.
- `DELETE /questions/<question_id>` — delete a question (and associated S3 media). Creator or admin only. Returns 409 if question is linked to an event; add `?confirm=true` to force deletion.
- `POST /questions/random` — returns one unseen question matching filters; body: `{"seen":[...],"filters":{...}}`; 404 when none available.

Example: list and create
```bash
curl -b cookiejar -c cookiejar http://localhost:5600/login -d 'username=me&password=pass'
curl -b cookiejar "http://localhost:5600/questions/?limit=5&tags=history,science"
curl -b cookiejar -H "Content-Type: application/json" \
  -d '{"question":"Capital of France?","answer":"Paris","added_by":"me","tags":["geography"]}' \
  http://localhost:5600/questions/
```

### Public user endpoints
- `POST /users/signup` — register a new account; body: `username`, `email`, `password`. Sends verification email (link + 6-digit code). Rate-limited by IP.
- `POST /users/verify` — verify email; body: `{"token": "..."}` or `{"code": "123456"}`. Accepts either the URL token or the 6-digit code. Auto-approves the account. Rate-limited by IP.
- `POST /users/resend-verification` — resend verification email; body: `{"email": "..."}`. Rate-limited per email.
- `POST /users/request-reset` — request password reset; body: `{"email": "..."}`. Rate-limited per email. Response does not reveal whether the email exists.
- `POST /users/reset` — reset password; body: `{"token": "...", "password": "..."}` or `{"code": "...", "password": "..."}`. Rate-limited by IP.
- `POST /users/me/password` — change password (logged-in); body: `{"current_password": "...", "new_password": "..."}`.
- `POST /users/me/email` — start email change (logged-in); body: `{"email": "..."}`. Sends verification email to new address. Rate-limited per email.

### Admin user endpoints
- `GET /users/` — list users.
- `GET /users/<username>` — fetch user by username.
- `POST /users/` — create user; body: `username`, `email`, `password`, optional `role`, `is_verified`, `is_approved`.
- `PUT /users/<username>` — update fields (`email`, `password`, `role`, `is_verified`, `is_approved`, `username`).
- `DELETE /users/<username>` — remove user.

### HTML rendering
`GET /questions/<question_id>` will render `question_detail.html` when the `Accept` header prefers HTML. Otherwise it returns JSON.

### Event endpoints (base `/events`)
- `GET /events/` — list events with pagination. Optional filter: `created_by`.
- `GET /events/<id>` — event detail including a leaderboard preview.
- `POST /events/` — create an event. Required: `name`. Optional: `date`, `location`, `team_score`, `max_score`, `description`. Auth required.
- `PUT /events/<id>` — update event fields. Auth required; creator or admin only.
- `DELETE /events/<id>` — delete event. Auth required; creator or admin only. Add `?delete_questions=true` to also delete linked questions.
- `GET /events/<id>/questions` — ordered list of questions in the event.
- `POST /events/<id>/questions` — add questions to an event; body: `{"question_ids": [...]}`. Auth required.
- `DELETE /events/<id>/questions/<qid>` — remove a question from the event. Auth required.
- `PUT /events/<id>/questions/order` — reorder questions; body: `{"question_ids": [...]}`. Auth required.
- `POST /events/<id>/replay` — start a replay (returns questions without answers).
- `POST /events/<id>/replay/submit` — submit answers and get scores; body: `{"answers": [{question_id, answer, override?}], "display_name"?}`. Logged-in users get persistent scores.
- `GET /events/<id>/leaderboard` — full leaderboard for the event.
