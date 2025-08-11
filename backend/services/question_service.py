import random
from backend.models.question import QuestionModel
from backend.db.questiondb import (
    get_question_by_id_db,
    get_all_questions_db,
    add_question_to_db,
    update_question_in_db,
    delete_question_from_db
)
from backend.db.files3 import upload_file_to_s3

def get_question_by_id(question_id: str) -> QuestionModel | None:
    """Fetch a question by ID from the database."""
    return get_question_by_id_db(question_id)

def get_all_questions(filters: dict = None) -> list[QuestionModel] | None:
    """Fetch all questions from the database, optionally filtered by provided criteria."""
    return get_all_questions_db(filters)

def create_question(data: dict) -> bool:
    """Create a new question in the database."""
    question = QuestionModel(**data)
    # If the question has a media file, upload it to S3 and get the URL
    media_file = data.get("media_file")
    if media_file:
        question.media_url = upload_file_to_s3(media_file)  # Assuming this function exists
    else:
        question.media_url = None
    return add_question_to_db(question)

def update_question(question_id: str, updates: dict, user: str) -> QuestionModel | None:
    """Update an existing question in the database."""
    updates["updated_by"] = user  # Add the user who made the update
    return update_question_in_db(question_id, updates)

def delete_question(question_id: str) -> bool:
    return delete_question_from_db(question_id)

def get_random_question_filtered(seen_ids: list = None, filters: dict = None):
    """Fetch a random reviewed question not in seen_ids with optional filters."""

    if seen_ids is None:
        seen_ids = []
    
    if filters is None:
        filters = {}
    filters["review_status"] = True

    items = get_all_questions_db(filters)

    if seen_ids:
        items = [q for q in items if q.get("id") not in seen_ids]

    if not items:
        return None

    return QuestionModel(**random.choice(items))