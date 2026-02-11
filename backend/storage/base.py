from __future__ import annotations

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
