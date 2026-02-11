from __future__ import annotations

from backend.db.files3 import delete_file_from_s3, upload_file_to_s3
from backend.db.questiondb import (
    add_question_to_db,
    delete_question_from_db,
    get_all_questions_db,
    get_question_by_id_db,
    update_question_in_db,
)
from backend.db.userdb import (
    add_user_to_db,
    delete_user_from_db,
    get_all_users_db,
    get_user_by_id_db,
    get_user_by_username_db,
    update_user_in_db,
)
from backend.storage.base import MediaStore, QuestionStore, UserStore


class DynamoQuestionStore(QuestionStore):
    def add(self, question):
        return add_question_to_db(question)

    def get_by_id(self, question_id):
        return get_question_by_id_db(question_id)

    def list(self, filters=None, limit: int = 50, last_key: dict | None = None):
        return get_all_questions_db(filters, limit=limit, last_key=last_key)

    def list_by_topic(self, topic: str, limit: int = 50, last_key: dict | None = None):
        return get_all_questions_db({"question_topic": topic}, limit=limit, last_key=last_key)

    def update(self, question_id: str, updates: dict):
        return update_question_in_db(question_id, updates)

    def delete(self, question_id: str) -> bool:
        return delete_question_from_db(question_id)


class DynamoUserStore(UserStore):
    def add(self, user):
        return add_user_to_db(user)

    def get_by_username(self, username: str):
        return get_user_by_username_db(username)

    def get_by_id(self, user_id: str):
        return get_user_by_id_db(user_id)

    def list(self, filters: dict | None = None):
        return get_all_users_db(filters)

    def update(self, user_id: str, updates: dict):
        return update_user_in_db(user_id, updates)

    def delete(self, user_id: str) -> bool:
        return delete_user_from_db(user_id)


class S3MediaStore(MediaStore):
    def upload(self, file):
        return upload_file_to_s3(file)

    def delete(self, media_path: str) -> bool:
        return delete_file_from_s3(media_path)

    def get_url(self, media_path: str, expires_in: int | None = None):
        return media_path
