### Questions storage (DynamoDB)

- **Table:** `TriviaQuestions` (overridable via `DYNAMODB_TABLE`)
- **Region:** `AWS_REGION` env var (default `eu-central-1`)
- **Item shape:** matches `QuestionModel` (`question_id` stored as `id` and `question_id` for backward compatibility), includes optional `media_url`, `update_history`, timestamps, tags, language, review_status, etc.
- **Access patterns:** current implementation uses scans with in-memory filtering; pagination uses DynamoDB `LastEvaluatedKey` exposed as a base64 `next_page_token`/`page_token`.
- **Pagination flow:** clients pass `limit`, `offset`, and optional `page_token`; the service decodes `page_token` into `ExclusiveStartKey`, scans, skips `offset`, and returns `next_page_token` (encoded `LastEvaluatedKey`).
- **Recommendations:** add GSIs for frequent filters (e.g., `review_status`, `language`, `tags`) and switch to queries; replace `offset` with pure token-based pagination to avoid skipped reads.
- **Media lifecycle:** `media_url` is stored in the item; deletes and media replacements are handled in the service layer with S3 cleanup.
