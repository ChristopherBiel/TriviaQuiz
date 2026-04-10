from __future__ import annotations

import random as _random
from abc import ABC, abstractmethod
from typing import Optional, IO

from backend.models.event import EventModel
from backend.models.live import LiveAnswerModel, LiveParticipantModel, LiveSessionModel
from backend.models.question import QuestionModel
from backend.models.replay import ReplayAttemptModel
from backend.models.user import UserModel


class QuestionStore(ABC):
    @abstractmethod
    def add(self, question: QuestionModel) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, question_id: str) -> Optional[QuestionModel]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        filters: dict | None = None,
        limit: int = 50,
        last_key: dict | None = None,
    ) -> tuple[list[QuestionModel], dict | None]:
        raise NotImplementedError

    @abstractmethod
    def list_by_topic(
        self,
        topic: str,
        limit: int = 50,
        last_key: dict | None = None,
    ) -> tuple[list[QuestionModel], dict | None]:
        raise NotImplementedError

    @abstractmethod
    def update(self, question_id: str, updates: dict) -> Optional[QuestionModel]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, question_id: str) -> bool:
        raise NotImplementedError

    def count(self, filters: dict | None = None) -> int:
        """Return total questions matching filters. Override for O(1) DB-level count."""
        items, _ = self.list(filters, limit=10_000)
        return len(items)

    def random_reviewed(
        self,
        seen_ids: list[str] | None = None,
        filters: dict | None = None,
    ) -> Optional[QuestionModel]:
        """Return a random reviewed question not in seen_ids. Override for DB-level random."""
        items, _ = self.list(filters, limit=10_000)
        if seen_ids:
            items = [q for q in items if q.question_id not in seen_ids]
        return _random.choice(items) if items else None


class UserStore(ABC):
    @abstractmethod
    def add(self, user: UserModel) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UserModel]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[UserModel]:
        raise NotImplementedError

    @abstractmethod
    def list(self, filters: dict | None = None) -> list[UserModel]:
        raise NotImplementedError

    @abstractmethod
    def update(self, user_id: str, updates: dict) -> Optional[UserModel]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        raise NotImplementedError

    def get_by_verification_token(self, token: str) -> Optional[UserModel]:
        """Find a user by verification token. Override for O(1) DB-level lookup."""
        for u in self.list():
            if u.verification_token == token:
                return u
        return None

    def get_by_verification_code(self, code: str) -> Optional[UserModel]:
        """Find a user by verification code. Override for O(1) DB-level lookup."""
        for u in self.list():
            if u.verification_code == code:
                return u
        return None

    def get_by_reset_token(self, token: str) -> Optional[UserModel]:
        """Find a user by reset token. Override for O(1) DB-level lookup."""
        for u in self.list():
            if u.reset_token == token:
                return u
        return None

    def get_by_reset_code(self, code: str) -> Optional[UserModel]:
        """Find a user by reset code. Override for O(1) DB-level lookup."""
        for u in self.list():
            if u.reset_code == code:
                return u
        return None

    def get_by_email(self, email: str) -> Optional[UserModel]:
        """Find a user by email. Override for O(1) DB-level lookup."""
        for u in self.list():
            if u.email == email:
                return u
        return None


class EventStore(ABC):
    @abstractmethod
    def add(self, event: EventModel) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, event_id: str) -> Optional[EventModel]:
        raise NotImplementedError

    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[EventModel]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        filters: dict | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EventModel], int]:
        raise NotImplementedError

    @abstractmethod
    def update(self, event_id: str, updates: dict) -> Optional[EventModel]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, event_id: str) -> bool:
        raise NotImplementedError


class ReplayStore(ABC):
    @abstractmethod
    def save(self, replay: ReplayAttemptModel) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, replay_id: str) -> Optional[ReplayAttemptModel]:
        raise NotImplementedError

    @abstractmethod
    def list_by_event(
        self, event_id: str, limit: int = 50, offset: int = 0
    ) -> list[ReplayAttemptModel]:
        raise NotImplementedError

    @abstractmethod
    def list_by_user(self, user_id: str) -> list[ReplayAttemptModel]:
        raise NotImplementedError

    @abstractmethod
    def get_leaderboard(
        self, event_id: str, limit: int = 10
    ) -> list[ReplayAttemptModel]:
        raise NotImplementedError

    @abstractmethod
    def has_user_played(self, event_id: str, user_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, replay_id: str) -> bool:
        raise NotImplementedError


class LiveStore(ABC):
    @abstractmethod
    def create_session(self, session: LiveSessionModel) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[LiveSessionModel]:
        raise NotImplementedError

    @abstractmethod
    def get_session_by_code(self, join_code: str) -> Optional[LiveSessionModel]:
        raise NotImplementedError

    @abstractmethod
    def update_session(self, session_id: str, updates: dict) -> Optional[LiveSessionModel]:
        raise NotImplementedError

    @abstractmethod
    def add_participant(self, participant: LiveParticipantModel) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_participants(self, session_id: str) -> list[LiveParticipantModel]:
        raise NotImplementedError

    @abstractmethod
    def get_participant(self, participant_id: str) -> Optional[LiveParticipantModel]:
        raise NotImplementedError

    @abstractmethod
    def save_answer(self, answer: LiveAnswerModel) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_answer(
        self, session_id: str, participant_id: str, question_index: int
    ) -> Optional[LiveAnswerModel]:
        raise NotImplementedError

    @abstractmethod
    def get_answers(
        self, session_id: str, question_index: Optional[int] = None
    ) -> list[LiveAnswerModel]:
        raise NotImplementedError

    @abstractmethod
    def get_participant_answers(
        self, session_id: str, participant_id: str
    ) -> list[LiveAnswerModel]:
        raise NotImplementedError

    @abstractmethod
    def update_answers_bulk(
        self, session_id: str, question_index: int, updates: dict
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def update_answer(self, answer_id: str, updates: dict) -> Optional[LiveAnswerModel]:
        raise NotImplementedError


class MediaStore(ABC):
    @abstractmethod
    def upload(self, file) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, media_path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_url(self, media_path: str, expires_in: int | None = None) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def download(self, media_path: str) -> tuple[IO[bytes], str | None, int | None]:
        raise NotImplementedError
