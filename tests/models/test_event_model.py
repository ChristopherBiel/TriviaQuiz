import pytest
from datetime import date

from backend.models.event import EventModel


def test_event_defaults():
    event = EventModel(name="Quiz Night", created_by="alice")
    assert event.event_id  # UUID generated
    assert event.name == "Quiz Night"
    assert event.created_by == "alice"
    assert event.question_ids == []
    assert event.date is None
    assert event.location is None
    assert event.team_score is None
    assert event.created_at is not None
    assert event.updated_at is not None


def test_event_with_all_fields():
    event = EventModel(
        name="Pub Quiz 42",
        date=date(2026, 1, 15),
        location="The Crown",
        team_score=25.5,
        best_score=30.0,
        max_score=40.0,
        description="Monthly pub quiz",
        question_ids=["q1", "q2"],
        created_by="bob",
    )
    assert event.date == date(2026, 1, 15)
    assert event.location == "The Crown"
    assert event.team_score == 25.5
    assert event.question_ids == ["q1", "q2"]


def test_event_name_required():
    with pytest.raises(Exception):
        EventModel(created_by="alice")


def test_event_created_by_required():
    with pytest.raises(Exception):
        EventModel(name="Quiz Night")


def test_event_sanitizes_strings():
    event = EventModel(
        name="  Quiz <script>alert('x')</script> Night  ",
        created_by="alice",
    )
    assert "<script>" not in event.name
    assert event.name == "Quiz  Night"


def test_event_serialization():
    event = EventModel(name="Quiz", created_by="alice")
    data = event.model_dump(mode="json")
    assert data["name"] == "Quiz"
    assert "event_id" in data
    assert "created_at" in data


def test_event_populate_by_name():
    event = EventModel(id="custom-id", name="Quiz", created_by="alice")
    assert event.event_id == "custom-id"
