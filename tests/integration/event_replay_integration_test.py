"""Integration tests for the event replay flow.

These tests mock only the storage layer, letting the full chain
API → service → answer evaluator run for real.  This catches contract
mismatches between layers that pure unit tests (which mock services) miss.
"""

import pytest
from flask import Flask
from unittest.mock import MagicMock

from backend.api import init_routes as init_api_routes
from backend.models.event import EventModel
from backend.models.question import QuestionModel
from backend.models.replay import ReplayAttemptModel


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

class MemoryEventStore:
    def __init__(self):
        self._data: dict[str, EventModel] = {}

    def add(self, event: EventModel) -> bool:
        self._data[event.event_id] = event
        return True

    def get_by_id(self, event_id: str):
        return self._data.get(event_id)

    def list(self, filters=None, limit=50, offset=0):
        items = list(self._data.values())
        return items[offset:offset + limit], len(items)

    def update(self, event_id: str, updates: dict):
        event = self._data.get(event_id)
        if not event:
            return None
        self._data[event_id] = event.model_copy(update=updates)
        return self._data[event_id]

    def delete(self, event_id: str) -> bool:
        return self._data.pop(event_id, None) is not None


class MemoryQuestionStore:
    def __init__(self):
        self._data: dict[str, QuestionModel] = {}

    def add(self, question: QuestionModel) -> bool:
        self._data[question.question_id] = question
        return True

    def get_by_id(self, qid: str):
        return self._data.get(qid)

    def update(self, qid: str, updates: dict, **_kw):
        q = self._data.get(qid)
        if not q:
            return None
        self._data[qid] = q.model_copy(update=updates)
        return self._data[qid]

    def delete(self, qid: str) -> bool:
        return self._data.pop(qid, None) is not None


class MemoryReplayStore:
    def __init__(self):
        self._data: list[ReplayAttemptModel] = []

    def save(self, replay: ReplayAttemptModel) -> bool:
        self._data.append(replay)
        return True

    def get_by_id(self, replay_id: str):
        return next((r for r in self._data if r.replay_id == replay_id), None)

    def list_by_event(self, event_id: str, limit=50, offset=0):
        return [r for r in self._data if r.event_id == event_id][offset:offset + limit]

    def list_by_user(self, user_id: str):
        return [r for r in self._data if r.user_id == user_id]

    def get_leaderboard(self, event_id: str, limit=10):
        matching = [r for r in self._data if r.event_id == event_id]
        return sorted(matching, key=lambda r: r.score, reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def stores():
    return {
        "event": MemoryEventStore(),
        "question": MemoryQuestionStore(),
        "replay": MemoryReplayStore(),
        "media": MagicMock(),  # media store — just a stub
    }


@pytest.fixture
def app(monkeypatch, stores):
    app = Flask(__name__)
    app.secret_key = "test"

    # Patch at every import site so the in-memory stores are used
    # regardless of how each module imported the factory function.
    for mod in (
        "backend.storage.factory",
        "backend.storage",
        "backend.services.event_service",
        "backend.services.replay_service",
        "backend.api.events",
    ):
        for name, store_key in [
            ("get_event_store", "event"),
            ("get_question_store", "question"),
            ("get_replay_store", "replay"),
            ("get_media_store", "media"),
        ]:
            try:
                monkeypatch.setattr(f"{mod}.{name}", lambda _k=store_key: stores[_k])
            except AttributeError:
                pass  # not every module imports every factory function

    stores["media"].get_url.return_value = None

    init_api_routes(app)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, username="tester", role="user"):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = username
        sess["role"] = role


def _seed_questions(store):
    """Create 3 questions and return their IDs."""
    questions = [
        QuestionModel(question="Capital of France?", answer="Paris", added_by="tester"),
        QuestionModel(question="Who painted the Mona Lisa?", answer="Leonardo da Vinci", added_by="tester"),
        QuestionModel(question="Chemical symbol for gold?", answer="Au", added_by="tester"),
    ]
    ids = []
    for q in questions:
        store.add(q)
        ids.append(q.question_id)
    return ids, questions


# ---------------------------------------------------------------------------
# Full replay flow: create event → add questions → replay → score → leaderboard
# ---------------------------------------------------------------------------

class TestFullReplayFlow:
    """End-to-end replay flow exercising API → service → evaluator."""

    def test_complete_replay_flow(self, client, stores):
        _login(client)
        qids, questions = _seed_questions(stores["question"])

        # 1. Create event
        resp = client.post("/api/events/", json={"name": "Quiz Night", "location": "The Pub"})
        assert resp.status_code == 201
        event_id = resp.get_json()["event_id"]

        # 2. Add questions
        resp = client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids})
        assert resp.status_code == 200
        assert resp.get_json()["added"] == qids

        # 3. Start replay — answers must NOT be included
        resp = client.post(f"/api/events/{event_id}/replay")
        assert resp.status_code == 200
        replay_data = resp.get_json()
        assert replay_data["total"] == 3
        for q in replay_data["questions"]:
            assert "answer" not in q
            assert "question" in q
            assert "question_id" in q

        # 4. Submit answers using the "answer" key (what the frontend sends)
        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "answer": "Paris"},        # exact match
                {"question_id": qids[1], "answer": "Da Vinci"},     # fuzzy — below threshold
                {"question_id": qids[2], "answer": "Au"},           # exact match
            ],
        })
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["score"] == 2
        assert result["total"] == 3
        # Verify individual answers came back correctly
        assert result["answers"][0]["is_correct"] is True
        assert result["answers"][0]["user_answer"] == "Paris"
        assert result["answers"][1]["is_correct"] is False
        assert result["answers"][1]["user_answer"] == "Da Vinci"
        assert result["answers"][2]["is_correct"] is True

        # 5. Leaderboard should include this replay
        resp = client.get(f"/api/events/{event_id}/leaderboard")
        assert resp.status_code == 200
        lb = resp.get_json()["items"]
        assert len(lb) == 1
        assert lb[0]["score"] == 2

    def test_replay_with_user_answer_key(self, client, stores):
        """The API must accept 'user_answer' as an alias for 'answer'."""
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Alt-Key Test"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids})

        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "user_answer": "Paris"},
                {"question_id": qids[1], "user_answer": "Leonardo da Vinci"},
                {"question_id": qids[2], "user_answer": "Au"},
            ],
        })
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["score"] == 3  # all correct
        assert all(a["is_correct"] for a in result["answers"])

    def test_replay_missing_answers_scores_zero(self, client, stores):
        """Submitting with empty answer strings should score 0."""
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Empty Answers"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids})

        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "answer": ""},
                {"question_id": qids[1], "answer": ""},
                {"question_id": qids[2], "answer": ""},
            ],
        })
        assert resp.status_code == 201
        assert resp.get_json()["score"] == 0


class TestReplayOverrides:
    """Manual override through the full stack."""

    def test_override_wrong_to_correct(self, client, stores):
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Override Test"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids[:1]})

        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "answer": "London", "override": True},
            ],
        })
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["score"] == 1
        assert result["answers"][0]["is_correct"] is True
        assert result["answers"][0]["user_answer"] == "London"

    def test_override_correct_to_wrong(self, client, stores):
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Override Test 2"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids[:1]})

        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "answer": "Paris", "override": False},
            ],
        })
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["score"] == 0
        assert result["answers"][0]["is_correct"] is False


class TestFuzzyMatching:
    """Verify fuzzy matching works through the full stack."""

    def test_case_insensitive_match(self, client, stores):
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Fuzzy Test"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids[:1]})

        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [{"question_id": qids[0], "answer": "PARIS"}],
        })
        assert resp.status_code == 201
        assert resp.get_json()["answers"][0]["is_correct"] is True

    def test_close_fuzzy_match(self, client, stores):
        """An answer very close to correct should pass fuzzy matching."""
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Fuzzy Close"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids[:1]})

        # "Parris" is close to "Paris" (ratio ~0.91, above 0.85)
        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [{"question_id": qids[0], "answer": "Parris"}],
        })
        assert resp.status_code == 201
        assert resp.get_json()["answers"][0]["is_correct"] is True

    def test_distant_fuzzy_no_match(self, client, stores):
        """An answer far from correct should not match."""
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Fuzzy Distant"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids[:1]})

        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [{"question_id": qids[0], "answer": "London"}],
        })
        assert resp.status_code == 201
        assert resp.get_json()["answers"][0]["is_correct"] is False


class TestQuestionStatsUpdated:
    """Verify that question statistics are updated through the full stack."""

    def test_times_asked_incremented(self, client, stores):
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Stats Test"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids[:2]})

        client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "answer": "Paris"},
                {"question_id": qids[1], "answer": "wrong"},
            ],
        })

        q0 = stores["question"].get_by_id(qids[0])
        q1 = stores["question"].get_by_id(qids[1])
        assert q0.times_asked == 1
        assert q0.times_correct == 1
        assert q0.times_incorrect == 0
        assert q1.times_asked == 1
        assert q1.times_correct == 0
        assert q1.times_incorrect == 1


class TestBestScoreTracking:
    """Verify event best_score is updated through the full stack."""

    def test_best_score_updated(self, client, stores):
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Best Score"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids})

        # First replay: 1/3
        client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "answer": "Paris"},
                {"question_id": qids[1], "answer": "wrong"},
                {"question_id": qids[2], "answer": "wrong"},
            ],
        })
        event = stores["event"].get_by_id(event_id)
        assert event.best_score == 1.0

        # Second replay: 3/3 — best_score should increase
        client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "answer": "Paris"},
                {"question_id": qids[1], "answer": "Leonardo da Vinci"},
                {"question_id": qids[2], "answer": "Au"},
            ],
        })
        event = stores["event"].get_by_id(event_id)
        assert event.best_score == 3.0

        # Third replay: 2/3 — best_score should NOT decrease
        client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [
                {"question_id": qids[0], "answer": "Paris"},
                {"question_id": qids[1], "answer": "Leonardo da Vinci"},
                {"question_id": qids[2], "answer": "wrong"},
            ],
        })
        event = stores["event"].get_by_id(event_id)
        assert event.best_score == 3.0


class TestLeaderboardOrdering:
    """Verify leaderboard sorts correctly through the full stack."""

    def test_leaderboard_sorted_by_score_desc(self, client, stores):
        _login(client)
        qids, _ = _seed_questions(stores["question"])

        resp = client.post("/api/events/", json={"name": "Leaderboard Test"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids})

        # Submit 3 replays with different scores
        for answers, name in [
            ([("wrong", "wrong", "wrong")], "Low"),
            ([("Paris", "Leonardo da Vinci", "Au")], "High"),
            ([("Paris", "wrong", "wrong")], "Mid"),
        ]:
            client.post(f"/api/events/{event_id}/replay/submit", json={
                "display_name": name,
                "answers": [
                    {"question_id": qids[i], "answer": answers[0][i]}
                    for i in range(3)
                ],
            })

        resp = client.get(f"/api/events/{event_id}/leaderboard")
        assert resp.status_code == 200
        lb = resp.get_json()["items"]
        assert len(lb) == 3
        assert lb[0]["display_name"] == "High"
        assert lb[0]["score"] == 3
        assert lb[1]["display_name"] == "Mid"
        assert lb[1]["score"] == 1
        assert lb[2]["display_name"] == "Low"
        assert lb[2]["score"] == 0


class TestAnonymousReplay:
    """Anonymous users can evaluate but not save to leaderboard."""

    def test_anonymous_evaluate_allowed(self, client, stores):
        # Login to create event and add questions
        _login(client)
        qids, _ = _seed_questions(stores["question"])
        resp = client.post("/api/events/", json={"name": "Anon Test"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids[:1]})

        # Logout
        with client.session_transaction() as sess:
            sess.clear()

        # Evaluate as anonymous — should work
        resp = client.post(f"/api/events/{event_id}/replay/evaluate", json={
            "answers": [{"question_id": qids[0], "answer": "Paris"}],
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result["score"] == 1

    def test_anonymous_submit_blocked(self, client, stores):
        # Login to create event and add questions
        _login(client)
        qids, _ = _seed_questions(stores["question"])
        resp = client.post("/api/events/", json={"name": "Anon Block Test"})
        event_id = resp.get_json()["event_id"]
        client.post(f"/api/events/{event_id}/questions", json={"question_ids": qids[:1]})

        # Logout
        with client.session_transaction() as sess:
            sess.clear()

        # Submit as anonymous — should be blocked
        resp = client.post(f"/api/events/{event_id}/replay/submit", json={
            "answers": [{"question_id": qids[0], "answer": "Paris"}],
        })
        assert resp.status_code == 403
