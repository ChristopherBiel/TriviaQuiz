from __future__ import annotations

from functools import lru_cache

from backend.core.settings import get_settings
from backend.storage.base import EventStore, LiveStore, MediaStore, QuestionStore, ReplayStore, UserStore


def _normalize_backend(value: str, default: str = "aws") -> str:
    if not value:
        return default
    normalized = value.strip().lower()
    aliases = {
        "dynamodb": "aws",
        "s3": "aws",
        "postgresql": "postgres",
    }
    return aliases.get(normalized, normalized)


@lru_cache()
def get_question_store() -> QuestionStore:
    settings = get_settings()
    backend = _normalize_backend(settings.question_store, settings.store_backend)

    if backend == "aws":
        from backend.storage.aws import DynamoQuestionStore

        return DynamoQuestionStore()

    if backend == "postgres":
        from backend.storage.postgres import PostgresQuestionStore

        return PostgresQuestionStore()

    raise RuntimeError(f"Unsupported question store backend: {backend}")


@lru_cache()
def get_user_store() -> UserStore:
    settings = get_settings()
    backend = _normalize_backend(settings.user_store, settings.store_backend)

    if backend == "aws":
        from backend.storage.aws import DynamoUserStore

        return DynamoUserStore()

    if backend == "postgres":
        from backend.storage.postgres import PostgresUserStore

        return PostgresUserStore()

    raise RuntimeError(f"Unsupported user store backend: {backend}")


@lru_cache()
def get_media_store() -> MediaStore:
    settings = get_settings()
    backend = _normalize_backend(settings.media_store, settings.store_backend)

    if backend == "aws":
        from backend.storage.aws import S3MediaStore

        return S3MediaStore()

    if backend == "minio":
        from backend.storage.minio import MinioMediaStore

        return MinioMediaStore()

    raise RuntimeError(f"Unsupported media store backend: {backend}")


@lru_cache()
def get_event_store() -> EventStore:
    from backend.storage.postgres import PostgresEventStore

    return PostgresEventStore()


@lru_cache()
def get_replay_store() -> ReplayStore:
    from backend.storage.postgres import PostgresReplayStore

    return PostgresReplayStore()


@lru_cache()
def get_live_store() -> LiveStore:
    from backend.storage.postgres import PostgresLiveStore

    return PostgresLiveStore()


def reset_store_cache() -> None:
    get_question_store.cache_clear()
    get_user_store.cache_clear()
    get_media_store.cache_clear()
    get_event_store.cache_clear()
    get_replay_store.cache_clear()
    get_live_store.cache_clear()
