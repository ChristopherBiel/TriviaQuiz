# ADR 0005: Storage Abstraction Layer

## Context
The application must support Postgres/MinIO now, while keeping the option to use AWS DynamoDB/S3 where needed. The service layer should not depend on backend-specific implementations.

## Decision
Introduce storage interfaces in `backend/storage/base.py` and select concrete adapters via `backend/storage/factory.py`.

## Consequences
- Services call `get_question_store()`, `get_user_store()`, and `get_media_store()` instead of concrete implementations.
- Adding a new backend requires implementing the interface but does not change service code.
- The codebase has an additional abstraction layer to maintain.

## Alternatives considered
- Directly importing adapters in service modules.
- Maintaining separate code paths for AWS vs non-AWS deployments.
