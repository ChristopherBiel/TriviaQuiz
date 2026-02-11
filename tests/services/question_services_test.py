# tests for question_service.py

"""
Unit tests for all functions in question_service.py.
- Should cover all CRUD operations.
- Should test both successful and failure cases.
- Should mock database interactions to isolate service logic.
- Should use pytest fixtures for setup.
- Should include tests for filtering and random question retrieval.
"""

import pytest
from backend.services.question_service import (
    get_question_by_id,
    get_all_questions,
    create_question,
    update_question,
    delete_question,
    get_random_question_filtered
)
from backend.models.question import QuestionModel
from unittest.mock import MagicMock
from types import SimpleNamespace

@pytest.fixture
def sample_question():
    return QuestionModel(
        question="Sample question?",
        answer="Sample answer",
        added_by="user123",
        question_topic="General",
        language="English",
        tags=["sample", "test"]
    )

@pytest.fixture
def sample_question_data():
    return {
        "question": "Sample question?",
        "answer": "Sample answer",
        "added_by": "user123",
        "question_topic": "General",
        "language": "English",
        "tags": ["sample", "test"]
    }

@pytest.fixture
def mock_stores(monkeypatch):
    question_store = MagicMock()
    media_store = MagicMock()
    question_store.get_by_id.return_value = None
    monkeypatch.setattr("backend.services.question_service.get_question_store", lambda: question_store)
    monkeypatch.setattr("backend.services.question_service.get_media_store", lambda: media_store)
    return SimpleNamespace(question_store=question_store, media_store=media_store)

def test_get_question_by_id(mock_stores, sample_question):
    """Test fetching a question by ID, where the ID is a uuid. It is automatically generated when the question is created."""
    sample_question_value = sample_question.model_dump()
    mock_stores.question_store.get_by_id.return_value = sample_question
    question = get_question_by_id(sample_question_value["question_id"])
    assert question is not None
    assert question.model_dump() == sample_question_value

def test_get_question_by_id_not_found(mock_stores):
    """Test fetching a question by ID that does not exist."""
    mock_stores.question_store.get_by_id.return_value = None
    question = get_question_by_id("nonexistent-id")
    assert question is None

def test_get_all_questions(mock_stores, sample_question):
    """Test fetching all questions with no filters."""
    mock_stores.question_store.list.return_value = ([sample_question], None)
    questions = get_all_questions()
    assert len(questions) == 1
    assert questions[0].model_dump() == sample_question.model_dump()

def test_get_all_questions_with_filters(mock_stores, sample_question):
    """Test fetching all questions with filters applied."""
    mock_stores.question_store.list.return_value = ([sample_question], None)
    filters = {"language": "English", "tags": ["sample"]}
    questions = get_all_questions(filters)
    assert len(questions) == 1
    assert questions[0].model_dump() == sample_question.model_dump()

def test_create_question(mock_stores, sample_question_data):
    """Test creating a new question."""
    mock_stores.question_store.add.return_value = True
    result = create_question(sample_question_data)
    assert isinstance(result, QuestionModel)
    assert result.question == sample_question_data["question"]
    mock_stores.question_store.add.assert_called_once()

def test_create_question_with_media(mock_stores, sample_question_data):
    """Test creating a new question with a media file."""
    mock_stores.question_store.add.return_value = True
    sample_question_data["media_file"] = "fake_media_file"
    mock_stores.media_store.upload.return_value = None
    result = create_question(sample_question_data)
    assert isinstance(result, QuestionModel)
    assert result.media_path is None
    mock_stores.media_store.upload.assert_called_once_with("fake_media_file")
    mock_stores.question_store.add.assert_called_once()

def test_create_question_with_media_success(mock_stores, sample_question_data):
    """Test creating a new question with a media file that uploads successfully."""
    sample_question_data["media_file"] = "fake_media_file"
    mock_stores.question_store.add.return_value = True
    mock_stores.media_store.upload.return_value = "s3://fake-bucket/fake_media_file"
    result = create_question(sample_question_data)
    assert isinstance(result, QuestionModel)
    mock_stores.question_store.add.assert_called_once()
    mock_stores.media_store.upload.assert_called_once_with("fake_media_file")
    assert result.media_path == "s3://fake-bucket/fake_media_file"

def test_update_question(mock_stores, sample_question):
    """Test updating an existing question."""
    sample_question_value = sample_question.model_dump()
    mock_stores.question_store.update.return_value = sample_question.model_copy(update={"question": "Updated question?"})
    updates = {"question": "Updated question?"}
    mock_stores.question_store.get_by_id.return_value = sample_question
    updated_question = update_question(sample_question_value["question_id"], updates, "user123", "admin")
    assert updated_question is not None
    assert updated_question.model_dump()["question"] == "Updated question?"
    assert updates["updated_by"] == "user123"
    mock_stores.question_store.update.assert_called_once_with(sample_question_value["question_id"], updates)

def test_update_question_not_found(mock_stores):
    """Test updating a question that does not exist."""
    mock_stores.question_store.update.return_value = None
    mock_stores.question_store.get_by_id.return_value = None
    updates = {"question": "Updated question?"}
    updated_question = update_question("nonexistent-id", updates, "user123")
    assert updated_question is None
    mock_stores.question_store.update.assert_called_once_with("nonexistent-id", updates)

def test_update_question_not_owner(mock_stores, sample_question):
    """Non-owner non-admin cannot update."""
    mock_stores.question_store.get_by_id.return_value = sample_question
    updates = {"question": "Updated question?"}
    updated_question = update_question(sample_question.question_id, updates, "other-user", "user")
    assert updated_question is None
    mock_stores.question_store.update.assert_not_called()

def test_update_question_admin_allowed(mock_stores, sample_question):
    """Admin can update any question."""
    mock_stores.question_store.get_by_id.return_value = sample_question
    mock_stores.question_store.update.return_value = sample_question.model_copy(update={"question": "Updated question?"})
    updates = {"question": "Updated question?"}
    updated_question = update_question(sample_question.question_id, updates, "admin", "admin")
    assert updated_question is not None
    mock_stores.question_store.update.assert_called_once()


def test_update_question_rejects_topic_change(mock_stores, sample_question):
    updates = {"question_topic": "New Topic"}
    with pytest.raises(ValueError):
        update_question(sample_question.question_id, updates, "admin", "admin")

def test_update_question_replaces_media(mock_stores, sample_question):
    """Updating with a new media file uploads and deletes the old one."""
    sample_question = sample_question.model_copy(update={"media_path": "old_url"})
    mock_stores.question_store.get_by_id.return_value = sample_question
    mock_stores.question_store.update.return_value = sample_question.model_copy(update={"media_path": "new_url"})

    mock_stores.media_store.upload.return_value = "new_url"
    updates = {"media_file": "fileobj"}
    updated = update_question(sample_question.question_id, updates, "user123")

    assert updated.media_path == "new_url"
    mock_stores.media_store.upload.assert_called_once_with("fileobj")
    mock_stores.media_store.delete.assert_called_once_with("old_url")
    assert updates["updated_by"] == "user123"
    mock_stores.question_store.update.assert_called_once_with(sample_question.question_id, {"media_path": "new_url", "updated_by": "user123"})

def test_update_question_remove_media(mock_stores, sample_question):
    """Setting media_path to None removes S3 asset."""
    sample_question = sample_question.model_copy(update={"media_path": "old_url"})
    mock_stores.question_store.get_by_id.return_value = sample_question
    mock_stores.question_store.update.return_value = sample_question.model_copy(update={"media_path": None})

    updates = {"media_path": None}
    updated = update_question(sample_question.question_id, updates, "user123")

    assert updated.media_path is None
    mock_stores.media_store.delete.assert_called_once_with("old_url")
    assert updates["updated_by"] == "user123"
    mock_stores.question_store.update.assert_called_once_with(sample_question.question_id, {"media_path": None, "updated_by": "user123"})

def test_delete_question(mock_stores, sample_question):
    """Test deleting a question."""
    sample_question_value = sample_question.model_dump()
    mock_stores.question_store.delete.return_value = True
    success = delete_question(sample_question_value["question_id"])
    assert success is True
    mock_stores.question_store.delete.assert_called_once_with(sample_question_value["question_id"])

def test_delete_question_with_media(mock_stores, sample_question):
    """Test deleting a question removes its media from S3."""
    sample_question = sample_question.model_copy(update={"media_path": "https://bucket.s3.region.amazonaws.com/file.png"})
    mock_stores.question_store.get_by_id.return_value = sample_question
    mock_stores.question_store.delete.return_value = True

    success = delete_question(sample_question.question_id)

    assert success is True
    mock_stores.media_store.delete.assert_called_once_with(sample_question.media_path)
    mock_stores.question_store.delete.assert_called_once_with(sample_question.question_id)

def test_delete_question_not_found(mock_stores):
    """Test deleting a question that does not exist."""
    mock_stores.question_store.delete.return_value = False
    success = delete_question("nonexistent-id")
    assert success is False
    mock_stores.question_store.delete.assert_called_once_with("nonexistent-id")

def test_get_random_question_filtered(mock_stores, sample_question):
    """Test fetching a random question that is not in seen_ids and matches filters."""
    mock_stores.question_store.list.return_value = ([sample_question], None)
    seen_ids = []
    filters = {"review_status": True}
    random_question = get_random_question_filtered(seen_ids, filters)
    assert random_question is not None
    assert random_question.model_dump() == sample_question.model_dump()
    mock_stores.question_store.list.assert_called_once_with(filters)
    mock_stores.question_store.list.reset_mock()
    # Test with seen_ids
    seen_ids = [sample_question.question_id]
    random_question = get_random_question_filtered(seen_ids, filters)
    assert random_question is None  # No unseen questions available
    mock_stores.question_store.list.assert_called_once_with(filters)
    mock_stores.question_store.list.reset_mock()
