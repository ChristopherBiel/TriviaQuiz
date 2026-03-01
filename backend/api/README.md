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
- `POST /questions/` — create a question. Required: `question`, `answer`, `added_by`. Optional: `incorrect_answers`, `question_topic`, `question_source`, `answer_source`, `language`, `tags`, `review_status`, `media_path`. Auth required. If `question_topic` is omitted, it defaults to `General`.
- `PUT /questions/<question_id>` — partial update. Auth required; only owner or admin can update. Accepts JSON or multipart with `media`. `question_topic` cannot be updated after creation.
- `DELETE /questions/<question_id>` — delete a question (and associated S3 media). Admin-only.
- `POST /questions/random` — returns one unseen question matching filters; body: `{"seen":[...],"filters":{...}}`; 404 when none available.

Example: list and create
```bash
curl -b cookiejar -c cookiejar http://localhost:5600/login -d 'username=me&password=pass'
curl -b cookiejar "http://localhost:5600/questions/?limit=5&tags=history,science"
curl -b cookiejar -H "Content-Type: application/json" \
  -d '{"question":"Capital of France?","answer":"Paris","added_by":"me","tags":["geography"]}' \
  http://localhost:5600/questions/
```

### User endpoints (admin-only)
- `GET /users/` — list users.
- `GET /users/<username>` — fetch user by username.
- `POST /users/` — create user; body: `username`, `email`, `password`, optional `role`, `is_verified`, `is_approved`.
- `PUT /users/<username>` — update fields (`email`, `password`, `role`, `is_verified`, `is_approved`, `username`).
- `DELETE /users/<username>` — remove user.

### HTML rendering
`GET /questions/<question_id>` will render `question_detail.html` when the `Accept` header prefers HTML. Otherwise it returns JSON.

### Event replay (roadmap)
The event replay API is stubbed in `backend/api/events.py` and is not yet registered in the app.
