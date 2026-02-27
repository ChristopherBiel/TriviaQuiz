import pytest
from flask import Flask
from backend.api import init_routes as init_api_routes
from backend.models.question import QuestionModel
import uuid


@pytest.fixture
def app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test"

    # In-memory store to simulate persistence
    store = {}

    def fake_create(data):
        q = QuestionModel(**data)
        store[q.question_id] = q
        return q

    def fake_get_all(filters=None, limit=None, offset=0, page_token=None, include_token=False):
        items = list(store.values())
        if filters and "review_status" in filters:
            items = [i for i in items if i.review_status == filters["review_status"]]
        sliced = items[offset: offset + limit] if limit else items
        return (sliced, None) if include_token else sliced

    def fake_update(qid, updates, user=None, role=None):
        if qid not in store:
            return None
        store[qid] = store[qid].model_copy(update=updates)
        return store[qid]

    def fake_delete(qid):
        return bool(store.pop(qid, None))

    def fake_random(seen, filters):
        for q in store.values():
            if q.question_id not in seen:
                return q
        return None

    def fake_count(filters=None):
        items = list(store.values())
        if filters and "review_status" in filters:
            items = [i for i in items if i.review_status == filters["review_status"]]
        return len(items)

    monkeypatch.setattr("backend.api.questions.create_question", fake_create)
    monkeypatch.setattr("backend.api.questions.get_all_questions", fake_get_all)
    monkeypatch.setattr("backend.api.questions.count_questions", fake_count)
    monkeypatch.setattr("backend.api.questions.update_question", fake_update)
    monkeypatch.setattr("backend.api.questions.delete_question", fake_delete)
    monkeypatch.setattr("backend.api.questions.get_random_question_filtered", fake_random)

    init_api_routes(app)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, role="user"):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = f"{role}-user"
        sess["role"] = role


def test_full_question_flow(client):
    login(client, role="user")
    payload = {
        "question": "What is 2+2?",
        "answer": "4",
        "added_by": "user-user",
        "tags": ["math"],
    }
    create_resp = client.post("/questions/", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    qid = created["question_id"]

    list_resp = client.get("/questions/?limit=10")
    assert list_resp.status_code == 200
    assert any(item["question_id"] == qid for item in list_resp.get_json()["items"])

    # Owner update
    login(client, role="user")
    update_resp = client.put(f"/questions/{qid}", json={"answer": "four"})
    assert update_resp.status_code == 200
    assert update_resp.get_json()["answer"] == "four"

    # Admin delete
    login(client, role="admin")
    delete_resp = client.delete(f"/questions/{qid}")
    assert delete_resp.status_code == 204

    # Random should now yield 404 since store empty
    random_resp = client.post("/questions/random", json={"seen": []})
    assert random_resp.status_code == 404
