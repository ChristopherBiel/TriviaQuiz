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
from unittest.mock import MagicMock, patch

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
def mock_db():
    db = MagicMock()
    db.get_question_by_id_db = MagicMock()
    db.get_all_questions_db = MagicMock()
    db.add_question_to_db = MagicMock()
    db.update_question_in_db = MagicMock()
    db.delete_question_from_db = MagicMock()
    return db

def test_get_question_by_id(mock_db, sample_question):
    """Test fetching a question by ID, where the ID is a uuid. It is automatically generated when the question is created."""
    sample_question_value = sample_question.model_dump()
    mock_db.get_question_by_id_db.return_value = sample_question
    question = get_question_by_id(sample_question_value["id"])
    assert question is not None
    assert question.model_dump() == sample_question_value

def test_get_question_by_id_not_found(mock_db):
    """Test fetching a question by ID that does not exist."""
    mock_db.get_question_by_id_db.return_value = None
    question = get_question_by_id("nonexistent-id")
    assert question is None

def test_get_all_questions(mock_db, sample_question):
    """Test fetching all questions with no filters."""
    mock_db.get_all_questions_db.return_value = [sample_question]
    questions = get_all_questions()
    assert len(questions) == 1
    assert questions[0].model_dump() == sample_question.model_dump()

def test_get_all_questions_with_filters(mock_db, sample_question):
    """Test fetching all questions with filters applied."""
    mock_db.get_all_questions_db.return_value = [sample_question]
    filters = {"language": "English", "tags": ["sample"]}
    questions = get_all_questions(filters)
    assert len(questions) == 1
    assert questions[0].model_dump() == sample_question.model_dump()

def test_create_question(mock_db, sample_question):
    """Test creating a new question."""
    mock_db.add_question_to_db.return_value = True
    result = create_question(sample_question_data())
    assert result is True
    mock_db.add_question_to_db.assert_called_once()

def test_create_question_with_media(mock_db, sample_question_data):
    """Test creating a new question with a media file."""
    sample_question_data["media_file"] = "fake_media_file"
    mock_db.add_question_to_db.return_value = True
    result = create_question(sample_question_data)
    assert result is False # Assuming media upload fails in this mock
    mock_db.add_question_to_db.assert_called_once()

def test_create_question_with_media_success(mock_db, sample_question_data):
    """Test creating a new question with a media file that uploads successfully."""
    sample_question_data["media_file"] = "fake_media_file"
    mock_db.add_question_to_db.return_value = True
    # Override the upload_file_to_s3 to simulate success
    with patch('backend.db.files3.upload_file_to_s3', return_value="s3://fake-bucket/fake_media_file") as mock_upload:
        result = create_question(sample_question_data)
        assert result is True
        mock_db.add_question_to_db.assert_called_once()
        mock_upload.assert_called_once_with("fake_media_file")
    # Check if the media_url is set correctly
    question = get_question_by_id(sample_question_data["id"])
    assert question.media_url == "s3://fake-bucket/fake_media_file"

def test_update_question(mock_db, sample_question):
    """Test updating an existing question."""
    sample_question_value = sample_question.model_dump()
    mock_db.update_question_in_db.return_value = sample_question
    updates = {"question": "Updated question?"}
    updated_question = update_question(sample_question_value["id"], updates, "user123")
    assert updated_question is not None
    assert updated_question.model_dump()["question"] == "Updated question?"
    mock_db.update_question_in_db.assert_called_once_with(sample_question_value["id"], updates)

def test_update_question_not_found(mock_db):
    """Test updating a question that does not exist."""
    mock_db.update_question_in_db.return_value = None
    updates = {"question": "Updated question?"}
    updated_question = update_question("nonexistent-id", updates, "user123")
    assert updated_question is None
    mock_db.update_question_in_db.assert_called_once_with("nonexistent-id", updates)

def test_delete_question(mock_db, sample_question):
    """Test deleting a question."""
    sample_question_value = sample_question.model_dump()
    mock_db.delete_question_from_db.return_value = True
    success = delete_question(sample_question_value["id"])
    assert success is True
    mock_db.delete_question_from_db.assert_called_once_with(sample_question_value["id"])

def test_delete_question_not_found(mock_db):
    """Test deleting a question that does not exist."""
    mock_db.delete_question_from_db.return_value = False
    success = delete_question("nonexistent-id")
    assert success is False
    mock_db.delete_question_from_db.assert_called_once_with("nonexistent-id")

def test_get_random_question_filtered(mock_db, sample_question):
    """Test fetching a random question that is not in seen_ids and matches filters."""
    mock_db.get_all_questions_db.return_value = [sample_question]
    seen_ids = []
    filters = {"review_status": True}
    random_question = get_random_question_filtered(seen_ids, filters)
    assert random_question is not None
    assert random_question.model_dump() == sample_question.model_dump()
    mock_db.get_all_questions_db.assert_called_once_with(filters)
    mock_db.get_all_questions_db.reset_mock()
    # Test with seen_ids
    seen_ids = [sample_question.id]
    random_question = get_random_question_filtered(seen_ids, filters)
    assert random_question is None  # No unseen questions available
    mock_db.get_all_questions_db.assert_called_once_with(filters)
    mock_db.get_all_questions_db.reset_mock()
