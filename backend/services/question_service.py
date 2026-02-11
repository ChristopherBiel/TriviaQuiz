import random
import json
from base64 import urlsafe_b64encode, urlsafe_b64decode
from backend.models.question import QuestionModel
from backend.db.questiondb import (
    get_question_by_id_db,
    get_all_questions_db,
    add_question_to_db,
    update_question_in_db,
    delete_question_from_db
)
from backend.db.files3 import upload_file_to_s3, delete_file_from_s3


def _encode_page_token(last_key):
    if not last_key:
        return None
    return urlsafe_b64encode(json.dumps(last_key).encode()).decode()


def _decode_page_token(token: str | None):
    if not token:
        return None
    try:
        return json.loads(urlsafe_b64decode(token.encode()).decode())
    except Exception:
        return None

def get_question_by_id(question_id: str) -> QuestionModel | None:
    """Fetch a question by ID from the database."""
    return get_question_by_id_db(question_id)

def get_all_questions(
    filters: dict = None,
    limit: int | None = 50,
    offset: int = 0,
    page_token: str | None = None,
    include_token: bool = False
) -> list[QuestionModel] | tuple[list[QuestionModel], str | None]:
    """Fetch questions with optional pagination token."""
    if limit is None:
        limit = 10_000  # safety cap for unbounded fetch

    start_key = _decode_page_token(page_token)

    collected: list[QuestionModel] = []
    last_key = start_key
    skipped = 0

    while len(collected) < limit:
        result = get_all_questions_db(filters, limit=limit, last_key=last_key)
        if isinstance(result, tuple):
            batch, last_key = result
        else:
            batch, last_key = result, None
        if skipped < offset:
            to_skip = min(offset - skipped, len(batch))
            batch = batch[to_skip:]
            skipped += to_skip
        collected.extend(batch)
        if not last_key or len(collected) >= limit:
            break

    collected = collected[:limit]
    next_token = _encode_page_token(last_key)
    if include_token:
        return collected, next_token
    return collected

def create_question(data: dict) -> QuestionModel | None:
    """Create a new question in the database."""
    media_file = data.get("media_file")
    question_payload = {k: v for k, v in data.items() if k != "media_file"}
    if not question_payload.get("question_topic"):
        question_payload["question_topic"] = "General"
    question = QuestionModel(**question_payload)
    # If the question has a media file, upload it to S3 and get the URL
    if media_file:
        question.media_path = upload_file_to_s3(media_file)
    else:
        question.media_path = None
    success = add_question_to_db(question)
    return question if success else None

def update_question(question_id: str, updates: dict, user: str | None = None, role: str | None = None) -> QuestionModel | None:
    """Update an existing question in the database."""
    if "question_topic" in updates:
        raise ValueError("question_topic cannot be updated after creation")
    media_file = updates.pop("media_file", None)
    remove_media = "media_path" in updates and updates.get("media_path") is None

    existing = get_question_by_id_db(question_id) if (media_file or remove_media or user) else None
    if (media_file or remove_media) and not existing:
        return None

    if existing and user and role != "admin" and user != existing.added_by:
        return None

    if media_file:
        new_media_path = upload_file_to_s3(media_file)
        if new_media_path:
            updates["media_path"] = new_media_path
            if existing and existing.media_path:
                delete_file_from_s3(existing.media_path)

    if remove_media and existing and existing.media_path:
        delete_file_from_s3(existing.media_path)

    if user:
        updates["updated_by"] = user  # Track who made the update when available
    return update_question_in_db(question_id, updates)

def delete_question(question_id: str) -> bool:
    question = get_question_by_id_db(question_id)
    media_path = getattr(question, "media_path", None) if question else None

    if media_path:
        delete_file_from_s3(media_path)

    return delete_question_from_db(question_id)

def get_random_question_filtered(seen_ids: list = None, filters: dict = None):
    """Fetch a random reviewed question not in seen_ids with optional filters."""

    if seen_ids is None:
        seen_ids = []
    
    effective_filters = dict(filters) if filters else {}
    effective_filters["review_status"] = True

    result = get_all_questions_db(effective_filters)
    if isinstance(result, tuple):
        items, _ = result
    else:
        items = result

    if seen_ids:
        items = [q for q in items if q.question_id not in seen_ids]

    if not items:
        return None

    return random.choice(items)


def get_question_metadata(filters: dict | None = None) -> dict:
    """Return distinct languages, topics, and tags for reviewed questions."""
    effective_filters = dict(filters) if filters else {}
    # Default to reviewed questions to match gameplay/admin expectations.
    effective_filters.setdefault("review_status", True)

    items = get_all_questions(effective_filters, limit=None)
    languages = sorted({q.language for q in items if q.language})
    topics = sorted({q.question_topic for q in items if q.question_topic})
    tags = sorted({tag for q in items for tag in (q.tags or [])})

    return {"languages": languages, "topics": topics, "tags": tags}
