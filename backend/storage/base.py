from __future__ import annotations

import random as _random
from abc import ABC, abstractmethod
from typing import Optional, IO

from backend.models.question import QuestionModel
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

    def get_by_reset_token(self, token: str) -> Optional[UserModel]:
        """Find a user by reset token. Override for O(1) DB-level lookup."""
        for u in self.list():
            if u.reset_token == token:
                return u
        return None


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
