from backend.models.replay import ReplayAttemptModel


def test_replay_defaults():
    replay = ReplayAttemptModel(event_id="e1", score=5, total=10)
    assert replay.replay_id  # UUID generated
    assert replay.event_id == "e1"
    assert replay.score == 5
    assert replay.total == 10
    assert replay.user_id is None
    assert replay.display_name is None
    assert replay.answers == []
    assert replay.completed_at is not None


def test_replay_with_all_fields():
    replay = ReplayAttemptModel(
        event_id="e1",
        user_id="u1",
        display_name="Alice",
        score=8,
        total=10,
        answers=[{"question_id": "q1", "user_answer": "A", "correct_answer": "A", "is_correct": True}],
    )
    assert replay.user_id == "u1"
    assert replay.display_name == "Alice"
    assert len(replay.answers) == 1


def test_replay_serialization():
    replay = ReplayAttemptModel(event_id="e1", score=3, total=5)
    data = replay.model_dump(mode="json")
    assert data["event_id"] == "e1"
    assert data["score"] == 3
    assert "replay_id" in data
    assert "completed_at" in data


def test_replay_populate_by_name():
    replay = ReplayAttemptModel(id="custom-id", event_id="e1", score=0, total=0)
    assert replay.replay_id == "custom-id"
