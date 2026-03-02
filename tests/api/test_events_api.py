import pytest
from flask import Flask
from unittest.mock import MagicMock, patch

from backend.api.events import events_bp
from backend.models.event import EventModel
from backend.models.replay import ReplayAttemptModel


@pytest.fixture
def app():
    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(events_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _login_session(client, username="tester", role="user"):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = username
        sess["role"] = role


def _sample_event(**overrides):
    defaults = {"name": "Quiz Night", "created_by": "tester"}
    defaults.update(overrides)
    return EventModel(**defaults)


# --- List events ---

def test_list_events(client, monkeypatch):
    event = _sample_event()
    monkeypatch.setattr("backend.api.events.list_events", MagicMock(return_value=([event], 1)))
    resp = client.get("/api/events/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["pagination"]["total"] == 1
    assert len(data["items"]) == 1


# --- Get event ---

def test_get_event(client, monkeypatch):
    event = _sample_event()
    monkeypatch.setattr("backend.api.events.get_event", MagicMock(return_value=event))
    monkeypatch.setattr("backend.api.events.get_leaderboard", MagicMock(return_value=[]))
    resp = client.get(f"/api/events/{event.event_id}")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Quiz Night"


def test_get_event_not_found(client, monkeypatch):
    monkeypatch.setattr("backend.api.events.get_event", MagicMock(return_value=None))
    resp = client.get("/api/events/bad-id")
    assert resp.status_code == 404


# --- Create event ---

def test_create_event_requires_auth(client):
    resp = client.post("/api/events/", json={"name": "Quiz Night"})
    assert resp.status_code == 403


def test_create_event_success(client, monkeypatch):
    _login_session(client)
    event = _sample_event()
    monkeypatch.setattr("backend.api.events.create_event", MagicMock(return_value=event))
    resp = client.post("/api/events/", json={"name": "Quiz Night"})
    assert resp.status_code == 201


def test_create_event_missing_name(client):
    _login_session(client)
    resp = client.post("/api/events/", json={"location": "Pub"})
    assert resp.status_code == 400


# --- Update event ---

def test_update_event_requires_auth(client):
    resp = client.put("/api/events/some-id", json={"name": "New"})
    assert resp.status_code == 403


def test_update_event_success(client, monkeypatch):
    _login_session(client)
    event = _sample_event(name="Updated")
    monkeypatch.setattr("backend.api.events.update_event", MagicMock(return_value=event))
    resp = client.put("/api/events/some-id", json={"name": "Updated"})
    assert resp.status_code == 200


def test_update_event_not_found(client, monkeypatch):
    _login_session(client)
    monkeypatch.setattr("backend.api.events.update_event", MagicMock(return_value=None))
    resp = client.put("/api/events/bad-id", json={"name": "x"})
    assert resp.status_code == 404


# --- Delete event ---

def test_delete_event_requires_auth(client):
    resp = client.delete("/api/events/some-id")
    assert resp.status_code == 403


def test_delete_event_success(client, monkeypatch):
    _login_session(client)
    monkeypatch.setattr("backend.api.events.delete_event", MagicMock(return_value=True))
    resp = client.delete("/api/events/some-id")
    assert resp.status_code == 204


def test_delete_event_not_found(client, monkeypatch):
    _login_session(client)
    monkeypatch.setattr("backend.api.events.delete_event", MagicMock(return_value=False))
    resp = client.delete("/api/events/bad-id")
    assert resp.status_code == 404


# --- Event questions ---

def test_add_questions_requires_auth(client):
    resp = client.post("/api/events/some-id/questions", json={"question_ids": ["q1"]})
    assert resp.status_code == 403


def test_add_questions_success(client, monkeypatch):
    _login_session(client)
    monkeypatch.setattr("backend.api.events.add_question_to_event", MagicMock(return_value=True))
    resp = client.post("/api/events/some-id/questions", json={"question_ids": ["q1", "q2"]})
    assert resp.status_code == 200
    assert resp.get_json()["added"] == ["q1", "q2"]


def test_remove_question_success(client, monkeypatch):
    _login_session(client)
    monkeypatch.setattr("backend.api.events.remove_question_from_event", MagicMock(return_value=True))
    resp = client.delete("/api/events/some-id/questions/q1")
    assert resp.status_code == 204


# --- Replay ---

def test_start_replay(client, monkeypatch):
    monkeypatch.setattr("backend.api.events.start_replay", MagicMock(return_value={
        "event_id": "e1", "name": "Quiz", "total": 2, "questions": [],
    }))
    resp = client.post("/api/events/e1/replay")
    assert resp.status_code == 200


def test_start_replay_not_found(client, monkeypatch):
    monkeypatch.setattr("backend.api.events.start_replay", MagicMock(return_value=None))
    resp = client.post("/api/events/bad-id/replay")
    assert resp.status_code == 404


def test_submit_replay(client, monkeypatch):
    replay = ReplayAttemptModel(event_id="e1", score=2, total=3, answers=[])
    monkeypatch.setattr("backend.api.events.submit_replay", MagicMock(return_value=replay))
    resp = client.post("/api/events/e1/replay/submit", json={
        "answers": [{"question_id": "q1", "answer": "A"}],
    })
    assert resp.status_code == 201
    assert resp.get_json()["score"] == 2


# --- Leaderboard ---

def test_leaderboard(client, monkeypatch):
    monkeypatch.setattr("backend.api.events.get_leaderboard", MagicMock(return_value=[
        {"display_name": "Alice", "score": 8, "total": 10},
    ]))
    resp = client.get("/api/events/e1/leaderboard")
    assert resp.status_code == 200
    assert len(resp.get_json()["items"]) == 1


# --- Reorder ---

def test_reorder_questions_success(client, monkeypatch):
    _login_session(client)
    monkeypatch.setattr("backend.api.events.reorder_event_questions", MagicMock(return_value=True))
    resp = client.put("/api/events/e1/questions/order", json={"question_ids": ["q2", "q1"]})
    assert resp.status_code == 200


def test_reorder_questions_invalid(client, monkeypatch):
    _login_session(client)
    monkeypatch.setattr("backend.api.events.reorder_event_questions", MagicMock(return_value=False))
    resp = client.put("/api/events/e1/questions/order", json={"question_ids": ["q3"]})
    assert resp.status_code == 400
