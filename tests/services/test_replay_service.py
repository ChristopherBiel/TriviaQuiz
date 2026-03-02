import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from backend.services.replay_service import (
    start_replay,
    submit_replay,
    get_leaderboard,
    get_user_replays,
)
from backend.models.event import EventModel
from backend.models.question import QuestionModel
from backend.models.replay import ReplayAttemptModel


@pytest.fixture
def sample_event():
    return EventModel(
        name="Quiz Night",
        created_by="alice",
        question_ids=["q1", "q2"],
    )


@pytest.fixture
def sample_questions():
    return {
        "q1": QuestionModel(question_id="q1", question="Capital of France?", answer="Paris", added_by="alice"),
        "q2": QuestionModel(question_id="q2", question="2+2?", answer="4", added_by="alice"),
    }


@pytest.fixture
def mock_stores(monkeypatch):
    event_store = MagicMock()
    question_store = MagicMock()
    replay_store = MagicMock()
    monkeypatch.setattr("backend.services.replay_service.get_event_store", lambda: event_store)
    monkeypatch.setattr("backend.services.replay_service.get_question_store", lambda: question_store)
    monkeypatch.setattr("backend.services.replay_service.get_replay_store", lambda: replay_store)
    return SimpleNamespace(event_store=event_store, question_store=question_store, replay_store=replay_store)


def test_start_replay(mock_stores, sample_event, sample_questions):
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.side_effect = lambda qid: sample_questions.get(qid)

    result = start_replay(sample_event.event_id)
    assert result is not None
    assert result["name"] == "Quiz Night"
    assert result["total"] == 2
    assert len(result["questions"]) == 2
    # Answers should NOT be included
    for q in result["questions"]:
        assert "answer" not in q


def test_start_replay_not_found(mock_stores):
    mock_stores.event_store.get_by_id.return_value = None
    assert start_replay("bad-id") is None


def test_submit_replay_correct_answers(mock_stores, sample_event, sample_questions):
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.side_effect = lambda qid: sample_questions.get(qid)
    mock_stores.replay_store.save.return_value = True
    mock_stores.question_store.update.return_value = None

    answers = [
        {"question_id": "q1", "answer": "Paris"},
        {"question_id": "q2", "answer": "4"},
    ]
    replay = submit_replay(sample_event.event_id, answers, user_id="u1", display_name="Alice")
    assert replay is not None
    assert replay.score == 2
    assert replay.total == 2


def test_submit_replay_wrong_answers(mock_stores, sample_event, sample_questions):
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.side_effect = lambda qid: sample_questions.get(qid)
    mock_stores.replay_store.save.return_value = True
    mock_stores.question_store.update.return_value = None

    answers = [
        {"question_id": "q1", "answer": "London"},
        {"question_id": "q2", "answer": "5"},
    ]
    replay = submit_replay(sample_event.event_id, answers)
    assert replay is not None
    assert replay.score == 0


def test_submit_replay_fuzzy_match(mock_stores, sample_event, sample_questions):
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.side_effect = lambda qid: sample_questions.get(qid)
    mock_stores.replay_store.save.return_value = True
    mock_stores.question_store.update.return_value = None

    answers = [
        {"question_id": "q1", "answer": "paris"},  # case insensitive
        {"question_id": "q2", "answer": "4"},
    ]
    replay = submit_replay(sample_event.event_id, answers)
    assert replay.score == 2


def test_submit_replay_with_override(mock_stores, sample_event, sample_questions):
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.side_effect = lambda qid: sample_questions.get(qid)
    mock_stores.replay_store.save.return_value = True
    mock_stores.question_store.update.return_value = None

    answers = [
        {"question_id": "q1", "answer": "London", "override": True},  # override to correct
        {"question_id": "q2", "answer": "4", "override": False},  # override to wrong
    ]
    replay = submit_replay(sample_event.event_id, answers)
    assert replay.score == 1


def test_submit_replay_increments_stats(mock_stores, sample_event, sample_questions):
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.side_effect = lambda qid: sample_questions.get(qid)
    mock_stores.replay_store.save.return_value = True
    mock_stores.question_store.update.return_value = None

    answers = [
        {"question_id": "q1", "answer": "Paris"},
        {"question_id": "q2", "answer": "5"},
    ]
    submit_replay(sample_event.event_id, answers)
    # q1 correct, q2 wrong
    calls = mock_stores.question_store.update.call_args_list
    assert len(calls) == 2
    # First call should increment times_asked and times_correct
    assert calls[0][0][1]["times_asked"] == 1
    assert "times_correct" in calls[0][0][1]
    # Second call should increment times_asked and times_incorrect
    assert calls[1][0][1]["times_asked"] == 1
    assert "times_incorrect" in calls[1][0][1]


def test_get_leaderboard(mock_stores):
    replay = ReplayAttemptModel(event_id="e1", score=8, total=10, display_name="Alice")
    mock_stores.replay_store.get_leaderboard.return_value = [replay]
    result = get_leaderboard("e1")
    assert len(result) == 1
    assert result[0]["display_name"] == "Alice"
    assert result[0]["score"] == 8


def test_get_user_replays(mock_stores):
    replay = ReplayAttemptModel(event_id="e1", score=5, total=10)
    mock_stores.replay_store.list_by_user.return_value = [replay]
    result = get_user_replays("u1")
    assert len(result) == 1
    assert result[0]["event_id"] == "e1"


def test_submit_replay_user_answer_key(mock_stores, sample_event, sample_questions):
    """The service must accept 'user_answer' as an alternative to 'answer'."""
    mock_stores.event_store.get_by_id.return_value = sample_event
    mock_stores.question_store.get_by_id.side_effect = lambda qid: sample_questions.get(qid)
    mock_stores.replay_store.save.return_value = True
    mock_stores.question_store.update.return_value = None

    answers = [
        {"question_id": "q1", "user_answer": "Paris"},
        {"question_id": "q2", "user_answer": "4"},
    ]
    replay = submit_replay(sample_event.event_id, answers)
    assert replay.score == 2
    assert replay.answers[0]["user_answer"] == "Paris"
    assert replay.answers[1]["user_answer"] == "4"
