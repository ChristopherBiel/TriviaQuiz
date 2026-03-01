#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import mimetypes
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlparse

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

from backend.models.question import QuestionModel
from backend.storage import get_media_store, get_question_store


@dataclass
class MigrationStats:
    seen: int = 0
    created: int = 0
    replaced: int = 0
    skipped_existing: int = 0
    failed: int = 0
    media_copied: int = 0
    media_failed: int = 0


class InMemoryUpload(io.BytesIO):
    """Minimal file-like object with filename, compatible with media stores."""

    def __init__(self, payload: bytes, filename: str):
        super().__init__(payload)
        self.filename = filename


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate questions from a source DynamoDB table into the configured target "
            "question store and copy referenced media from source S3 into the configured target media store."
        )
    )
    parser.add_argument(
        "--source-region",
        default=os.getenv("SOURCE_AWS_REGION") or os.getenv("AWS_REGION", "eu-central-1"),
        help="AWS region for source DynamoDB/S3",
    )
    parser.add_argument(
        "--source-profile",
        default=os.getenv("SOURCE_AWS_PROFILE") or os.getenv("AWS_PROFILE"),
        help="Optional AWS profile for source credentials",
    )
    parser.add_argument(
        "--source-endpoint-url",
        default=os.getenv("SOURCE_AWS_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL"),
        help="Optional shared endpoint URL for source DynamoDB/S3 (e.g. LocalStack)",
    )
    parser.add_argument(
        "--source-dynamodb-endpoint-url",
        default=os.getenv("SOURCE_DYNAMODB_ENDPOINT_URL"),
        help="Optional endpoint override for source DynamoDB",
    )
    parser.add_argument(
        "--source-s3-endpoint-url",
        default=os.getenv("SOURCE_S3_ENDPOINT_URL"),
        help="Optional endpoint override for source S3",
    )
    parser.add_argument(
        "--source-dynamodb-table",
        default=os.getenv("SOURCE_DYNAMODB_TABLE") or os.getenv("DYNAMODB_TABLE", "TriviaQuestions"),
        help="Source DynamoDB table containing questions",
    )
    parser.add_argument(
        "--source-s3-bucket",
        default=os.getenv("SOURCE_AWS_S3_BUCKET") or os.getenv("AWS_S3_BUCKET", "chris-trivia-media-bucket"),
        help="Default source S3 bucket containing question media",
    )
    parser.add_argument(
        "--fallback-added-by",
        default="migration",
        help="Fallback added_by value for malformed source rows missing added_by",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of source questions to process",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace existing target questions with matching IDs",
    )
    parser.add_argument(
        "--allow-missing-media",
        action="store_true",
        help="Continue migrating a question when media copy fails by clearing media_path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be migrated without writing to target stores",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-question progress",
    )
    return parser.parse_args()


def _coerce_decimal_types(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, list):
        return [_coerce_decimal_types(item) for item in value]
    if isinstance(value, dict):
        return {k: _coerce_decimal_types(v) for k, v in value.items()}
    return value


def _iter_source_items(source_table, limit: int | None = None) -> Iterator[dict[str, Any]]:
    emitted = 0
    scan_kwargs: dict[str, Any] = {}
    while True:
        response = source_table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            yield item
            emitted += 1
            if limit is not None and emitted >= limit:
                return
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return
        scan_kwargs["ExclusiveStartKey"] = last_key


def _extract_bucket_and_key(media_path: str, default_bucket: str) -> tuple[str | None, str | None]:
    raw = (media_path or "").strip()
    if not raw:
        return None, None

    if raw.startswith("s3://"):
        without_scheme = raw[len("s3://") :]
        parts = without_scheme.split("/", 1)
        if len(parts) != 2:
            return None, None
        return parts[0], unquote(parts[1])

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        host = parsed.netloc.lower()
        path = unquote(parsed.path.lstrip("/"))
        if not path:
            return None, None

        # Virtual-hosted S3 URL: <bucket>.s3.<region>.amazonaws.com/<key>
        virtual_host_match = re.match(r"^(?P<bucket>[a-z0-9][a-z0-9.-]+)\.s3[.-].*$", host)
        if virtual_host_match:
            return virtual_host_match.group("bucket"), path

        # Path-style S3 URL: s3.<region>.amazonaws.com/<bucket>/<key>
        if host == "s3.amazonaws.com" or host.startswith("s3.") or host.startswith("s3-"):
            parts = path.split("/", 1)
            if len(parts) == 2:
                return parts[0], parts[1]
            return default_bucket, path

        # Generic endpoints where path includes bucket.
        if path.startswith(f"{default_bucket}/"):
            return default_bucket, path[len(default_bucket) + 1 :]

        # Unknown host: do not assume this is source S3.
        return None, None

    if parsed.scheme:
        return None, None

    # Already a raw object key (or "<bucket>/<key>").
    key = raw.lstrip("/")
    if key.startswith(f"{default_bucket}/"):
        key = key[len(default_bucket) + 1 :]
    if not key:
        return None, None
    return default_bucket, key


def _filename_for_upload(source_key: str, content_type: str | None) -> str:
    name = Path(source_key).name or "media"
    if "." not in name:
        guessed_ext = mimetypes.guess_extension(content_type or "") or ""
        guessed_ext = guessed_ext.lstrip(".")
        if guessed_ext:
            name = f"{name}.{guessed_ext}"
        else:
            name = f"{name}.bin"
    return name


def _copy_media(
    source_s3_client,
    source_bucket: str,
    source_key: str,
    target_media_store,
    dry_run: bool,
) -> str:
    if dry_run:
        return f"dry-run://{source_bucket}/{source_key}"

    response = source_s3_client.get_object(Bucket=source_bucket, Key=source_key)
    body = response.get("Body")
    try:
        payload = body.read() if body else b""
    finally:
        if body is not None:
            body.close()

    upload_name = _filename_for_upload(source_key, response.get("ContentType"))
    upload_file = InMemoryUpload(payload, upload_name)
    target_media_path = target_media_store.upload(upload_file)
    if not target_media_path:
        raise RuntimeError(f"Target media store rejected upload for source key '{source_key}'")
    return target_media_path


def _question_from_source_item(item: dict[str, Any], fallback_added_by: str) -> QuestionModel:
    payload = _coerce_decimal_types(item)
    source_id = payload.get("question_id") or payload.get("id")
    if source_id:
        payload["question_id"] = str(source_id)
    payload.pop("id", None)

    if not payload.get("question_topic"):
        payload["question_topic"] = "General"
    if not payload.get("added_by"):
        payload["added_by"] = fallback_added_by

    return QuestionModel(**payload)


def _source_session(profile_name: str | None):
    resolved = profile_name or os.environ.get("SOURCE_AWS_PROFILE") or None
    if resolved:
        return boto3.session.Session(profile_name=resolved)
    # Create session without a profile. Temporarily remove AWS_PROFILE from the
    # environment if it is set to an empty string, because botocore treats any
    # non-None value (including "") as a profile name and raises ProfileNotFound.
    stashed = os.environ.pop("AWS_PROFILE", None)
    try:
        return boto3.session.Session()
    finally:
        if stashed is not None:
            os.environ["AWS_PROFILE"] = stashed


def main() -> int:
    args = _parse_args()

    source_dynamodb_endpoint = args.source_dynamodb_endpoint_url or args.source_endpoint_url
    source_s3_endpoint = args.source_s3_endpoint_url or args.source_endpoint_url

    session = _source_session(args.source_profile)
    dynamodb = session.resource(
        "dynamodb",
        region_name=args.source_region,
        endpoint_url=source_dynamodb_endpoint,
    )
    source_table = dynamodb.Table(args.source_dynamodb_table)
    source_s3_client = session.client(
        "s3",
        region_name=args.source_region,
        endpoint_url=source_s3_endpoint,
    )

    target_question_store = get_question_store()
    target_media_store = get_media_store()

    print(
        "Migrating questions from "
        f"DynamoDB table '{args.source_dynamodb_table}' (region={args.source_region}) "
        f"to target store '{target_question_store.__class__.__name__}'."
    )
    print(f"Target media store: {target_media_store.__class__.__name__}")
    if args.dry_run:
        print("Dry-run enabled: no writes will be performed.")

    stats = MigrationStats()
    media_cache: dict[str, str] = {}

    for source_item in _iter_source_items(source_table, limit=args.limit):
        stats.seen += 1

        try:
            question = _question_from_source_item(source_item, args.fallback_added_by)
        except ValidationError as exc:
            stats.failed += 1
            print(f"[{stats.seen}] Skipped invalid question payload: {exc.errors()[0]['msg']}")
            continue

        existing = target_question_store.get_by_id(question.question_id)
        if existing and not args.replace_existing:
            stats.skipped_existing += 1
            if args.verbose:
                print(f"[{stats.seen}] Skipped existing question {question.question_id}")
            continue

        if question.media_path:
            bucket, key = _extract_bucket_and_key(question.media_path, args.source_s3_bucket)
            if not bucket or not key:
                stats.media_failed += 1
                if args.allow_missing_media:
                    question.media_path = None
                    print(
                        f"[{stats.seen}] Could not parse media_path for question {question.question_id}; "
                        "continuing without media."
                    )
                else:
                    stats.failed += 1
                    print(
                        f"[{stats.seen}] Failed to parse media_path for question {question.question_id}; "
                        "use --allow-missing-media to continue without media."
                    )
                    continue
            else:
                source_media_ref = f"{bucket}/{key}"
                if source_media_ref in media_cache:
                    question.media_path = media_cache[source_media_ref]
                else:
                    try:
                        mapped_media_path = _copy_media(
                            source_s3_client=source_s3_client,
                            source_bucket=bucket,
                            source_key=key,
                            target_media_store=target_media_store,
                            dry_run=args.dry_run,
                        )
                    except (BotoCoreError, ClientError, RuntimeError) as exc:
                        stats.media_failed += 1
                        if args.allow_missing_media:
                            question.media_path = None
                            print(
                                f"[{stats.seen}] Failed media copy for {question.question_id}: {exc}. "
                                "Continuing without media."
                            )
                        else:
                            stats.failed += 1
                            print(
                                f"[{stats.seen}] Failed media copy for {question.question_id}: {exc}. "
                                "Use --allow-missing-media to continue."
                            )
                            continue
                    else:
                        media_cache[source_media_ref] = mapped_media_path
                        question.media_path = mapped_media_path
                        stats.media_copied += 1

        if args.dry_run:
            if existing:
                stats.replaced += 1
            else:
                stats.created += 1
            if args.verbose:
                action = "replace" if existing else "create"
                print(f"[{stats.seen}] Would {action} question {question.question_id}")
            continue

        if existing and args.replace_existing:
            if not target_question_store.delete(question.question_id):
                stats.failed += 1
                print(f"[{stats.seen}] Failed to delete existing question {question.question_id}")
                continue
            if not target_question_store.add(question):
                stats.failed += 1
                print(f"[{stats.seen}] Failed to insert replacement question {question.question_id}")
                continue
            stats.replaced += 1
            if args.verbose:
                print(f"[{stats.seen}] Replaced question {question.question_id}")
            continue

        if not target_question_store.add(question):
            stats.failed += 1
            print(f"[{stats.seen}] Failed to insert question {question.question_id}")
            continue

        stats.created += 1
        if args.verbose:
            print(f"[{stats.seen}] Created question {question.question_id}")

    print("")
    print("Migration summary")
    print(f"  Seen: {stats.seen}")
    print(f"  Created: {stats.created}")
    print(f"  Replaced: {stats.replaced}")
    print(f"  Skipped existing: {stats.skipped_existing}")
    print(f"  Media copied: {stats.media_copied}")
    print(f"  Media failures: {stats.media_failed}")
    print(f"  Failed records: {stats.failed}")

    return 1 if stats.failed else 0


if __name__ == "__main__":
    sys.exit(main())
