from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _normalize_backend(value: str | None, default: str) -> str:
    if not value:
        return default
    return value.strip().lower()


@dataclass(frozen=True)
class Settings:
    secret_key: str
    upload_folder: str
    allowed_extensions: frozenset[str]

    store_backend: str
    question_store: str
    user_store: str
    media_store: str
    media_proxy: bool
    media_url_expires_seconds: int

    aws_region: str
    aws_endpoint_url: str | None
    dynamodb_table: str
    users_table: str
    aws_s3_bucket: str

    postgres_dsn: str
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_auto_create: bool

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_region: str
    minio_secure: bool
    minio_auto_create_bucket: bool


@lru_cache()
def get_settings() -> Settings:
    allowed = os.getenv("ALLOWED_EXTENSIONS", "png,jpg,jpeg,gif,mp3,mp4")
    allowed_extensions = frozenset(ext.strip().lower() for ext in allowed.split(",") if ext.strip())

    store_backend = _normalize_backend(os.getenv("STORE_BACKEND"), "postgres")

    media_default = "minio" if store_backend != "aws" else "aws"

    return Settings(
        secret_key=os.getenv("SECRET_KEY", "default_secret_key"),
        upload_folder=os.getenv("UPLOAD_FOLDER", "static/uploads"),
        allowed_extensions=allowed_extensions,
        store_backend=store_backend,
        question_store=_normalize_backend(os.getenv("QUESTION_STORE"), store_backend),
        user_store=_normalize_backend(os.getenv("USER_STORE"), store_backend),
        media_store=_normalize_backend(os.getenv("MEDIA_STORE"), media_default),
        media_proxy=_as_bool(os.getenv("MEDIA_PROXY"), True),
        media_url_expires_seconds=_as_int(os.getenv("MEDIA_URL_EXPIRES_SECONDS"), 3600),
        aws_region=os.getenv("AWS_REGION", "eu-central-1"),
        aws_endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        dynamodb_table=os.getenv("DYNAMODB_TABLE", "TriviaQuestions"),
        users_table=os.getenv("USERS_TABLE", "TriviaUsersDev"),
        aws_s3_bucket=os.getenv("AWS_S3_BUCKET", "chris-trivia-media-bucket"),
        postgres_dsn=os.getenv("POSTGRES_DSN", ""),
        postgres_host=os.getenv("POSTGRES_HOST", "postgres"),
        postgres_port=_as_int(os.getenv("POSTGRES_PORT"), 5432),
        postgres_db=os.getenv("POSTGRES_DB", "trivia"),
        postgres_user=os.getenv("POSTGRES_USER", "trivia"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "trivia"),
        postgres_auto_create=_as_bool(os.getenv("POSTGRES_AUTO_CREATE"), True),
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
        minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_bucket=os.getenv("MINIO_BUCKET", "trivia-media"),
        minio_region=os.getenv("MINIO_REGION", "us-east-1"),
        minio_secure=_as_bool(os.getenv("MINIO_SECURE"), False),
        minio_auto_create_bucket=_as_bool(os.getenv("MINIO_AUTO_CREATE_BUCKET"), True),
    )
