from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy import (
    Boolean,
    Column,
    Date as sa_Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    desc,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

from backend.core.settings import get_settings
from backend.models.event import EventModel
from backend.models.question import QuestionModel
from backend.models.replay import ReplayAttemptModel
from backend.models.user import UserModel
from backend.storage.base import EventStore, QuestionStore, ReplayStore, UserStore

Base = declarative_base()


class QuestionRecord(Base):
    __tablename__ = "questions"

    question_id = Column(String, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    added_by = Column(String, nullable=False)
    added_at = Column(DateTime, nullable=False, default=_utcnow)
    question_topic = Column(String)
    event_id = Column(String)
    source_note = Column(String)
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


class EventRecord(Base):
    __tablename__ = "events"

    event_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    date = Column(sa_Date)
    location = Column(String)
    team_score = Column(Float)
    best_score = Column(Float)
    max_score = Column(Float)
    description = Column(Text)
    question_ids = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_events_name", "name"),
        Index("ix_events_created_by", "created_by"),
    )


class ReplayRecord(Base):
    __tablename__ = "event_replays"

    replay_id = Column(String, primary_key=True)
    event_id = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    answers = Column(JSONB, nullable=False)
    completed_at = Column(DateTime, nullable=False, default=_utcnow)


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
        event_id=record.event_id,
        source_note=record.source_note,
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
            event_id=question.event_id,
            source_note=question.source_note,
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

    def count(self, filters: dict | None = None) -> int:
        with session_scope() as session:
            query = select(func.count(QuestionRecord.question_id))
            query = _apply_question_filters(query, filters)
            return session.execute(query).scalar() or 0

    def random_reviewed(
        self,
        seen_ids: list[str] | None = None,
        filters: dict | None = None,
    ) -> QuestionModel | None:
        with session_scope() as session:
            query = select(QuestionRecord)
            query = _apply_question_filters(query, filters)
            if seen_ids:
                query = query.where(~QuestionRecord.question_id.in_(seen_ids))
            query = query.order_by(func.random()).limit(1)
            record = session.execute(query).scalars().first()
            return _question_from_record(record) if record else None


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

    def get_by_verification_token(self, token: str) -> UserModel | None:
        with session_scope() as session:
            query = select(UserRecord).where(UserRecord.verification_token == token)
            record = session.execute(query).scalars().first()
            return _user_from_record(record) if record else None

    def get_by_reset_token(self, token: str) -> UserModel | None:
        with session_scope() as session:
            query = select(UserRecord).where(UserRecord.reset_token == token)
            record = session.execute(query).scalars().first()
            return _user_from_record(record) if record else None


# ---------------------------------------------------------------------------
# Event helpers
# ---------------------------------------------------------------------------

def _event_from_record(record: EventRecord) -> EventModel:
    return EventModel(
        event_id=record.event_id,
        name=record.name,
        date=record.date,
        location=record.location,
        team_score=record.team_score,
        best_score=record.best_score,
        max_score=record.max_score,
        description=record.description,
        question_ids=list(record.question_ids or []),
        created_by=record.created_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _replay_from_record(record: ReplayRecord) -> ReplayAttemptModel:
    return ReplayAttemptModel(
        replay_id=record.replay_id,
        event_id=record.event_id,
        user_id=record.user_id,
        display_name=record.display_name,
        score=record.score,
        total=record.total,
        answers=list(record.answers or []),
        completed_at=record.completed_at,
    )


# ---------------------------------------------------------------------------
# PostgresEventStore
# ---------------------------------------------------------------------------

class PostgresEventStore(EventStore):
    def add(self, event: EventModel) -> bool:
        record = EventRecord(
            event_id=event.event_id,
            name=event.name,
            date=event.date,
            location=event.location,
            team_score=event.team_score,
            best_score=event.best_score,
            max_score=event.max_score,
            description=event.description,
            question_ids=list(event.question_ids or []),
            created_by=event.created_by,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
        with session_scope() as session:
            session.add(record)
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    def get_by_id(self, event_id: str) -> EventModel | None:
        with session_scope() as session:
            record = session.get(EventRecord, event_id)
            return _event_from_record(record) if record else None

    def list(
        self,
        filters: dict | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EventModel], int]:
        with session_scope() as session:
            query = select(EventRecord)
            count_query = select(func.count(EventRecord.event_id))

            if filters:
                for key, value in filters.items():
                    if value is None:
                        continue
                    col = getattr(EventRecord, key, None)
                    if col is not None:
                        query = query.filter(col == value)
                        count_query = count_query.filter(col == value)

            total = session.execute(count_query).scalar() or 0
            query = query.order_by(EventRecord.created_at.desc(), EventRecord.event_id)
            query = query.offset(offset).limit(limit)
            records = session.execute(query).scalars().all()
            return [_event_from_record(r) for r in records], total

    def update(self, event_id: str, updates: dict) -> EventModel | None:
        with session_scope(commit=True) as session:
            record = session.get(EventRecord, event_id)
            if not record:
                return None
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = _utcnow()
            session.add(record)
            return _event_from_record(record)

    def delete(self, event_id: str) -> bool:
        with session_scope(commit=True) as session:
            record = session.get(EventRecord, event_id)
            if not record:
                return False
            session.delete(record)
            return True


# ---------------------------------------------------------------------------
# PostgresReplayStore
# ---------------------------------------------------------------------------

class PostgresReplayStore(ReplayStore):
    def save(self, replay: ReplayAttemptModel) -> bool:
        record = ReplayRecord(
            replay_id=replay.replay_id,
            event_id=replay.event_id,
            user_id=replay.user_id,
            display_name=replay.display_name,
            score=replay.score,
            total=replay.total,
            answers=list(replay.answers or []),
            completed_at=replay.completed_at,
        )
        with session_scope() as session:
            session.add(record)
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    def get_by_id(self, replay_id: str) -> ReplayAttemptModel | None:
        with session_scope() as session:
            record = session.get(ReplayRecord, replay_id)
            return _replay_from_record(record) if record else None

    def list_by_event(
        self, event_id: str, limit: int = 50, offset: int = 0
    ) -> list[ReplayAttemptModel]:
        with session_scope() as session:
            query = (
                select(ReplayRecord)
                .where(ReplayRecord.event_id == event_id)
                .order_by(desc(ReplayRecord.score), ReplayRecord.completed_at)
                .offset(offset)
                .limit(limit)
            )
            records = session.execute(query).scalars().all()
            return [_replay_from_record(r) for r in records]

    def list_by_user(self, user_id: str) -> list[ReplayAttemptModel]:
        with session_scope() as session:
            query = (
                select(ReplayRecord)
                .where(ReplayRecord.user_id == user_id)
                .order_by(ReplayRecord.completed_at.desc())
            )
            records = session.execute(query).scalars().all()
            return [_replay_from_record(r) for r in records]

    def get_leaderboard(
        self, event_id: str, limit: int = 10
    ) -> list[ReplayAttemptModel]:
        with session_scope() as session:
            query = (
                select(ReplayRecord)
                .where(ReplayRecord.event_id == event_id)
                .order_by(desc(ReplayRecord.score), ReplayRecord.completed_at)
                .limit(limit)
            )
            records = session.execute(query).scalars().all()
            return [_replay_from_record(r) for r in records]

    def has_user_played(self, event_id: str, user_id: str) -> bool:
        with session_scope() as session:
            query = (
                select(ReplayRecord.replay_id)
                .where(ReplayRecord.event_id == event_id, ReplayRecord.user_id == user_id)
                .limit(1)
            )
            return session.execute(query).scalar() is not None
