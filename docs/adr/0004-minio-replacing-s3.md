# ADR 0004: MinIO Replacing S3

## Context
Media uploads were stored in S3. The new environment must avoid AWS dependencies while keeping S3-compatible behavior.

## Decision
Use MinIO as the object storage backend, accessed through the S3 API via boto3 (`backend/storage/minio.py`).

## Consequences
- Media storage is self-hosted and must be backed up.
- The app can either proxy media via `/media/*` (`MEDIA_PROXY=1`) or return presigned URLs (`MEDIA_PROXY=0`).
- MinIO credentials and bucket configuration become operational concerns.

## Alternatives considered
- Continue using AWS S3.
- Store media on the local filesystem.
- Use another S3-compatible object store.
