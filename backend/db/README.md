## Questions storage (DynamoDB + S3)

### Environment
- `AWS_REGION` (default `eu-central-1`)
- `DYNAMODB_TABLE` (default `TriviaQuestions`)
- `AWS_S3_BUCKET` (default `chris-trivia-media-bucket`)

### DynamoDB schema
- Partition key: `id` (a UUID). Some legacy paths also store `question_id`; both are populated for compatibility.
- Optional sort key: `question_topic` is included when present to support topic-level uniqueness for admin routes.
- Item shape mirrors `backend.models.question.QuestionModel`: question/answer text, incorrect answers, language, tags, review_status, update_history, timestamps, and optional `media_path`.

### Access patterns
- Reads/writes use table scans today with in-memory filtering for tags/language/topic/review_status. Pagination uses DynamoDB `LastEvaluatedKey`, encoded as base64 `next_page_token`/`page_token`.
- Flow: client passes `limit`, `offset`, optional `page_token`; service decodes token into `ExclusiveStartKey`, scans, skips `offset`, and returns `next_page_token`. `total` is best-effort via a capped scan.
- Recommendation: add GSIs for `review_status`, `language`, `tags` (or composite) and favor token-only pagination to avoid skipped reads.

### Media lifecycle (S3)
- Uploads accept limited extensions (`jpg,jpeg,png,gif,mp4,mp3`), infer MIME type, and write to `AWS_S3_BUCKET`.
- Items store the resulting URL in `media_path`; deletes/updates remove the previous S3 object when applicable.
- Keep bucket policy aligned with how you serve media (public-read vs presigned URLs).

### Local testing tips
- Point SDK to LocalStack or a sandbox account by exporting `AWS_ENDPOINT_URL`/`AWS_PROFILE`.
- Create the DynamoDB table with the `id` partition key (and `question_topic` sort key if desired) before running tests or the app.
