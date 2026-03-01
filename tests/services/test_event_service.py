import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from backend.services.event_service import (
    create_event,
    get_event,
    list_events,
    update_event,
    delete_event,
    add_question_to_event,
    remove_question_from_event,
    reorder_event_questions,
    get_event_questions,
)
from backend.models.event import EventModel
from backend.models.question import QuestionModel


@pytest.fixture
def sample_event():
    return EventModel(name="Quiz Night", created_by="alice")


@pytest.fixture
def sample_question():
    return QuestionModel(question="Q?", answer="A", added_by="alice")


@pytest.fixture
def mock_stores(monkeypatch):
    event_store = MagicMock()
    question_store = MagicMock()
    media_store = MagicMock()
    monkeypatch.setattr("backend.services.event_service.get_event_store", lambda: event_store)
    monkeypatch.setattr("backend.services.event_service.get_question_store", lambda: question_store)
    monkeypatch.setattr("backend.services.event_service.get_media_store", lambda: media_store)
    return SimpleNamespace(event_store=event_store, question_store=question_store, media_store=media_store)


def test_create_event(mock_stores):
    mock_stores.event_store.add.return_value = True
    result = create_event({"name": "Quiz Night"}, "alice")
    assert result is not None
    assert result.name == "Quiz Night"
    assert result.created_by == "alice"
    mock_stores.event_store.add.assert_called_once()


def test_create_event_failure(mock_stores):
    mock_stores.event_store.add.return_value = False
    result = create_event({"name": "Quiz Night"}, "alice")
    assert result is None


def test_get_event(mock_stores, sample_event):
    mock_stores.event_store.get_by_id.return_value = sample_event
    result = get_event(sample_event.event_id)
    assert result == sample_event


def test_list_events(mock_stores, sample_event):
    mock_stores.event_store.list.return_value = ([sample_event], 1)
    events, total = list_events()
    assert len(events) == 1
    assert total == 1


def test_update_event_owner(mock_stores, sample_event):
    mock_stores.event_store.get_by_id.return_value = sample_event
    updated = sample_event.model_copy(update={"name": "Updated"})
    mock_stores.event_store.update.return_value = updated
    result = update_event(sample_event.event_id, {"name": "Updated"}, "alice", "user")
    assert result.name == "Updated"


def test_update_event_admin(mock_stores, sample_event):
    mock_stores.event_store.get_by_id.return_value = sample_event
    updated = sample_event.model_copy(update={"name": "Updated"})
    mock_stores.event_store.update.return_value = updated
    result = update_event(sample_event.event_id, {"name": "Updated"}, "bob", "admin")
    assert result.name == "Updated"


def test_update_event_unauthorized(mock_stores, sample_event):
    mock_stores.event_store.get_by_id.return_value = sample_event
    result = update_event(sample_event.event_id, {"name": "Updated"}, "bob", "user")
    assert result is None


def test_update_event_not_found(mock_stores):
    mock_stores.event_store.get_by_id.return_value = None
    result = update_event("bad-id", {"name": "Updated"}, "alice", "admin")
    assert result is None


def test_delete_event_owner(mock_stores, sample_event):
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.event_store.delete.return_value = True
    assert delete_event(sample_event.event_id, "alice", "user") is True


def test_delete_event_unauthorized(mock_stores, sample_event):
    mock_stores.event_store.get_by_id.return_value = sample_event
    assert delete_event(sample_event.event_id, "bob", "user") is False


def test_delete_event_cascade(mock_stores, sample_event, sample_question):
    sample_event = sample_event.model_copy(update={"question_ids": [sample_question.question_id]})
    sample_question_with_media = sample_question.model_copy(update={"media_path": "some/path"})
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.event_store.delete.return_value = True
    mock_stores.question_store.get_by_id.return_value = sample_question_with_media

    assert delete_event(sample_event.event_id, "alice", "user", delete_questions=True) is True
    mock_stores.question_store.delete.assert_called_once_with(sample_question.question_id)
    mock_stores.media_store.delete.assert_called_once_with("some/path")


def test_add_question_to_event(mock_stores, sample_event, sample_question):
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.return_value = sample_question
    assert add_question_to_event(sample_event.event_id, sample_question.question_id) is True
    mock_stores.event_store.update.assert_called_once()
    mock_stores.question_store.update.assert_called_once()


def test_add_question_event_not_found(mock_stores, sample_question):
    mock_stores.event_store.get_by_id.return_value = None
    assert add_question_to_event("bad-id", sample_question.question_id) is False


def test_remove_question_from_event(mock_stores, sample_event, sample_question):
    sample_event = sample_event.model_copy(update={"question_ids": [sample_question.question_id]})
    sample_question = sample_question.model_copy(update={"event_id": sample_event.event_id})
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.return_value = sample_question
    assert remove_question_from_event(sample_event.event_id, sample_question.question_id) is True
    mock_stores.event_store.update.assert_called_once()
    mock_stores.question_store.update.assert_called_once()


def test_reorder_event_questions(mock_stores, sample_event):
    sample_event = sample_event.model_copy(update={"question_ids": ["q1", "q2", "q3"]})
    mock_stores.event_store.get_by_id.return_value = sample_event
    assert reorder_event_questions(sample_event.event_id, ["q3", "q1", "q2"]) is True


def test_reorder_event_questions_invalid(mock_stores, sample_event):
    sample_event = sample_event.model_copy(update={"question_ids": ["q1", "q2"]})
    mock_stores.event_store.get_by_id.return_value = sample_event
    assert reorder_event_questions(sample_event.event_id, ["q1", "q3"]) is False


def test_get_event_questions(mock_stores, sample_event, sample_question):
    sample_event = sample_event.model_copy(update={"question_ids": [sample_question.question_id]})
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.return_value = sample_question
    questions = get_event_questions(sample_event.event_id)
    assert len(questions) == 1
    assert questions[0].question_id == sample_question.question_id
