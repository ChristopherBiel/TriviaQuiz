import pytest
from flask import Flask
from unittest.mock import MagicMock

from backend.api.questions import questions_bp


class DummyQuestion:
    def __init__(self, identifier):
        self.identifier = identifier

    def model_dump(self, mode="json"):
        return {"id": self.identifier}


@pytest.fixture
def app():
    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(questions_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _login_session(client, role="user"):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"
        sess["role"] = role


def test_list_questions_invalid_limit(client):
    resp = client.get("/questions/?limit=abc")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_list_questions_pagination_and_filters(client, monkeypatch):
    mock_get_all = MagicMock()
    mock_get_all.side_effect = [
        ([DummyQuestion("2"), DummyQuestion("3")], "token-123"),  # paged result
        [DummyQuestion("1"), DummyQuestion("2"), DummyQuestion("3")],  # total probe
    ]
    monkeypatch.setattr("backend.api.questions.get_all_questions", mock_get_all)

    resp = client.get("/questions/?limit=2&offset=1&tags=a,b&review_status=true&language=en")

    assert resp.status_code == 200
    assert mock_get_all.call_count == 2
    mock_get_all.assert_any_call({"tags": ["a", "b"], "review_status": True, "language": "en"}, limit=2, offset=1, page_token=None, include_token=True)
    mock_get_all.assert_any_call({"tags": ["a", "b"], "review_status": True, "language": "en"}, limit=None)

    data = resp.get_json()
    assert data["pagination"] == {"limit": 2, "offset": 1, "count": 2, "total": 3, "next_page_token": "token-123"}
    assert [item["id"] for item in data["items"]] == ["2", "3"]


def test_create_question_validation(client):
    _login_session(client)
    resp = client.post("/questions/", json={"question": "Q", "answer": "A"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_question_success(client, monkeypatch):
    mock_create = MagicMock(return_value=DummyQuestion("123"))
    monkeypatch.setattr("backend.api.questions.create_question", mock_create)

    payload = {
        "question": "Q",
        "answer": "A",
        "added_by": "tester",
        "tags": "tag1, tag2",
        "incorrect_answers": "x,y",
        "review_status": "yes",
    }

    _login_session(client, role="user")
    resp = client.post("/questions/", json=payload)

    assert resp.status_code == 201
    mock_create.assert_called_once_with({
        "question": "Q",
        "answer": "A",
        "added_by": "tester",
        "tags": ["tag1", "tag2"],
        "incorrect_answers": ["x", "y"],
        "review_status": True,
    })
    assert resp.get_json()["id"] == "123"


def test_update_question_invalid_fields(client):
    _login_session(client)
    resp = client.put("/questions/any-id", json={"unknown": "value"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_update_requires_auth(client):
    resp = client.put("/questions/any-id", json={"question": "ok"})
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "Unauthorized"


def test_update_enforces_owner(client, monkeypatch):
    mock_update = MagicMock(return_value=None)
    monkeypatch.setattr("backend.api.questions.update_question", mock_update)
    _login_session(client, role="user")

    resp = client.put("/questions/any-id", json={"question": "ok"})

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Question not found or not permitted"
    mock_update.assert_called_once_with("any-id", {"question": "ok"}, "tester")


def test_delete_requires_admin(client):
    _login_session(client, role="user")
    resp = client.delete("/questions/any-id")
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "Forbidden"


def test_delete_question_authorized(client, monkeypatch):
    mock_delete = MagicMock(return_value=True)
    monkeypatch.setattr("backend.api.questions.delete_question", mock_delete)
    _login_session(client, role="admin")

    resp = client.delete("/questions/any-id")

    assert resp.status_code == 204
    mock_delete.assert_called_once_with("any-id")


def test_random_question_invalid_filters(client):
    resp = client.post("/questions/random", json={"filters": {"tags": 123}})
    assert resp.status_code == 400
    assert "error" in resp.get_json()
