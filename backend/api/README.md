### Questions API

This module exposes CRUD endpoints for questions plus filtered/paginated listing and random selection.

- **Base path:** `/questions`

#### List questions
- **GET** `/questions/`
- **Query params:** `limit` (default 50, >=1), `offset` (default 0, >=0), `page_token` (from previous response), `tags` (comma separated), `language`, `question_topic`, `review_status` (`true/false`).
- **Response:** `{"items":[...], "pagination":{"limit":n,"offset":n,"count":n,"total":n,"next_page_token":str|null}}`
- **Notes:** Filtering is applied before slicing; `review_status` is parsed as a boolean; tags are normalized to a string list; invalid `limit/offset` or malformed filters return `400`. Pagination uses DynamoDB `LastEvaluatedKey` encoded as `next_page_token`; pass it back as `page_token` for the next page. `total` is best-effort via a capped scan.

#### Get by id
- **GET** `/questions/<question_id>`
- **404** if not found.

#### Create
- **POST** `/questions/`
- **Body (JSON):** required `question`, `answer`, `added_by`; optional `incorrect_answers` (list or comma-separated string), `question_topic`, `language`, `tags`, `review_status`, `media_url`.
- **Auth:** requires logged-in user session.
- **201** with created record; **400** on missing/invalid payload; **403** when not logged in.

#### Update
- **PUT** `/questions/<question_id>`
- **Body (JSON):** partial updates accepted; same shape as create. Set `media_url` to `null` to remove media (S3 asset is deleted).
- **Auth:** requires logged-in user session.
- **Permissions:** only the original author (`added_by`) or an admin can update.
- **200** with updated record, **404** if not found or not permitted, **400** on missing/invalid payload; **403** when not logged in.

#### Delete
- **DELETE** `/questions/<question_id>`
- **Auth:** requires admin session.
- **204** on success, **404** if not found, **403** when not authorized. Media is cleaned up from S3 when present.

#### Random (filtered, unseen)
- **POST** `/questions/random`
- **Body (JSON):** `seen` (list of IDs), `filters` (same shape as list query).
- **404** when no unseen question matches.

### Users API (admin-only)

- **GET** `/users/` — list all users.
- **GET** `/users/<username>` — fetch a user by username.
- **POST** `/users/` — create a user; body: `username`, `email`, `password`, optional `role` (admin only), `is_verified`, `is_approved`.
- **PUT** `/users/<username>` — update user; body may include `email`, `password`, `role`, `is_verified`, `is_approved`.
- **DELETE** `/users/<username>` — delete user.
- All user endpoints require admin session; responses are JSON; errors use `{error: string}` with `400/403/404` as appropriate.
