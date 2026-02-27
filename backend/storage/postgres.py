from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    or_,
    select,
    text,
)
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

from backend.core.settings import get_settings
from backend.models.question import QuestionModel
from backend.models.user import UserModel
from backend.storage.base import QuestionStore, UserStore

Base = declarative_base()


class QuestionRecord(Base):
    __tablename__ = "questions"

    question_id = Column(String, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    added_by = Column(String, nullable=False)
    added_at = Column(DateTime, nullable=False, default=_utcnow)
    question_topic = Column(String)
    question_source = Column(String)
    answer_source = Column(String)

    incorrect_answers = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    times_asked = Column(Integer, nullable=False, default=0, server_default=text("0"))
    times_correct = Column(Integer, nullable=False, default=0, server_default=text("0"))
    times_incorrect = Column(Integer, nullable=False, default=0, server_default=text("0"))

    update_history = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    last_updated_at = Column(DateTime, nullable=False, default=_utcnow)

    language = Column(String)
    tags = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    review_status = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    media_path = Column(String)

    __table_args__ = (
        Index("ix_questions_topic_id", "question_topic", "question_id"),
        Index("ix_questions_review_status", "review_status"),
        Index("ix_questions_language", "language"),
    )


class UserRecord(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user", server_default=text("'user'"))
    is_verified = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_approved = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    verification_token = Column(String)
    verification_expires_at = Column(DateTime)
    reset_token = Column(String)
    reset_expires_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow)
    last_login_at = Column(DateTime)
    last_login_ip = Column(String)


def _build_url() -> URL | str:
    settings = get_settings()
    if settings.postgres_dsn:
        return settings.postgres_dsn
    return URL.create(
        "postgresql+psycopg2",
        username=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


@lru_cache()
def get_engine():
    engine = create_engine(
        _build_url(),
        pool_pre_ping=True,
        future=True,
    )
    return engine


@lru_cache()
def _get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False, future=True)


@lru_cache()
def _ensure_schema() -> None:
    settings = get_settings()
    if settings.postgres_auto_create:
        Base.metadata.create_all(bind=get_engine())


@contextmanager
def session_scope(commit: bool = False):
    _ensure_schema()
    session = _get_session_factory()()
    try:
        yield session
        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _question_from_record(record: QuestionRecord) -> QuestionModel:
    return QuestionModel(
        question_id=record.question_id,
        question=record.question,
        answer=record.answer,
        added_by=record.added_by,
        added_at=record.added_at,
        question_topic=record.question_topic,
        question_source=record.question_source,
        answer_source=record.answer_source,
        incorrect_answers=list(record.incorrect_answers or []),
        times_asked=record.times_asked,
        times_correct=record.times_correct,
        times_incorrect=record.times_incorrect,
        update_history=list(record.update_history or []),
        last_updated_at=record.last_updated_at,
        language=record.language,
        tags=list(record.tags or []),
        review_status=record.review_status,
        media_path=record.media_path,
    )


def _user_from_record(record: UserRecord) -> UserModel:
    return UserModel(
        user_id=record.user_id,
        username=record.username,
        email=record.email,
        password_hash=record.password_hash,
        role=record.role,
        is_verified=record.is_verified,
        is_approved=record.is_approved,
        verification_token=record.verification_token,
        verification_expires_at=record.verification_expires_at,
        reset_token=record.reset_token,
        reset_expires_at=record.reset_expires_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_login_at=record.last_login_at,
        last_login_ip=record.last_login_ip,
    )


def _apply_question_filters(query, filters: dict | None):
    if not filters:
        return query
    for key, value in filters.items():
        if value is None:
            continue
        if key == "tags" and isinstance(value, list):
            if value:
                query = query.filter(or_(*[QuestionRecord.tags.contains([tag]) for tag in value]))
            continue
        column = getattr(QuestionRecord, key, None)
        if column is not None:
            query = query.filter(column == value)
    return query


def _apply_user_filters(query, filters: dict | None):
    if not filters:
        return query
    for key, value in filters.items():
        if value is None:
            continue
        column = getattr(UserRecord, key, None)
        if column is not None:
            query = query.filter(column == value)
    return query


class PostgresQuestionStore(QuestionStore):
    def add(self, question: QuestionModel) -> bool:
        record = QuestionRecord(
            question_id=question.question_id,
            question=question.question,
            answer=question.answer,
            added_by=question.added_by,
            added_at=question.added_at,
            question_topic=question.question_topic,
            question_source=question.question_source,
            answer_source=question.answer_source,
            incorrect_answers=list(question.incorrect_answers or []),
            times_asked=question.times_asked,
            times_correct=question.times_correct,
            times_incorrect=question.times_incorrect,
            update_history=list(question.update_history or []),
            last_updated_at=question.last_updated_at,
            language=question.language,
            tags=list(question.tags or []),
            review_status=question.review_status,
            media_path=question.media_path,
        )
        with session_scope() as session:
            session.add(record)
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    def get_by_id(self, question_id: str) -> QuestionModel | None:
        with session_scope() as session:
            record = session.get(QuestionRecord, question_id)
            return _question_from_record(record) if record else None

    def list(self, filters: dict | None = None, limit: int = 50, last_key: dict | None = None):
        offset = 0
        if last_key and "offset" in last_key:
            try:
                offset = int(last_key["offset"])
            except (TypeError, ValueError):
                offset = 0
        with session_scope() as session:
            query = select(QuestionRecord)
            query = _apply_question_filters(query, filters)
            query = query.order_by(QuestionRecord.added_at.desc(), QuestionRecord.question_id)
            query = query.offset(offset).limit(limit + 1)
            records = session.execute(query).scalars().all()
            next_key = None
            if len(records) > limit:
                records = records[:limit]
                next_key = {"offset": offset + limit}
            return [_question_from_record(record) for record in records], next_key

    def list_by_topic(self, topic: str, limit: int = 50, last_key: dict | None = None):
        filters = {"question_topic": topic}
        return self.list(filters=filters, limit=limit, last_key=last_key)

    def update(self, question_id: str, updates: dict) -> QuestionModel | None:
        with session_scope(commit=True) as session:
            record = session.get(QuestionRecord, question_id)
            if not record:
                return None

            timestamp = _utcnow().isoformat()
            updated_by = updates.get("updated_by")
            changes = {k: v for k, v in updates.items() if k != "updated_by"}
            update_entry = {"timestamp": timestamp, "changes": changes}
            if updated_by is not None:
                update_entry["updated_by"] = updated_by

            history = list(record.update_history or [])
            history.append(update_entry)
            record.update_history = history

            for key, value in changes.items():
                if hasattr(record, key):
                    setattr(record, key, value)

            record.last_updated_at = _utcnow()
            session.add(record)
            return _question_from_record(record)

    def delete(self, question_id: str) -> bool:
        with session_scope(commit=True) as session:
            record = session.get(QuestionRecord, question_id)
            if not record:
                return False
            session.delete(record)
            return True


class PostgresUserStore(UserStore):
    def add(self, user: UserModel) -> bool:
        record = UserRecord(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            is_verified=user.is_verified,
            is_approved=user.is_approved,
            verification_token=user.verification_token,
            verification_expires_at=user.verification_expires_at,
            reset_token=user.reset_token,
            reset_expires_at=user.reset_expires_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            last_login_ip=user.last_login_ip,
        )
        with session_scope() as session:
            session.add(record)
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    def get_by_username(self, username: str) -> UserModel | None:
        with session_scope() as session:
            query = select(UserRecord).where(UserRecord.username == username)
            record = session.execute(query).scalars().first()
            return _user_from_record(record) if record else None

    def get_by_id(self, user_id: str) -> UserModel | None:
        with session_scope() as session:
            record = session.get(UserRecord, user_id)
            return _user_from_record(record) if record else None

    def list(self, filters: dict | None = None) -> list[UserModel]:
        with session_scope() as session:
            query = select(UserRecord)
            query = _apply_user_filters(query, filters)
            query = query.order_by(UserRecord.created_at.desc(), UserRecord.user_id)
            records = session.execute(query).scalars().all()
            return [_user_from_record(record) for record in records]

    def update(self, user_id: str, updates: dict) -> UserModel | None:
        with session_scope(commit=True) as session:
            record = session.get(UserRecord, user_id)
            if not record:
                return None

            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)

            record.updated_at = _utcnow()
            session.add(record)
            return _user_from_record(record)

    def delete(self, user_id: str) -> bool:
        with session_scope(commit=True) as session:
            record = session.get(UserRecord, user_id)
            if not record:
                return False
            session.delete(record)
            return True
