import pytest

from backend.main import create_app


@pytest.fixture
def app(monkeypatch):
    app = create_app()
    app.testing = True
    monkeypatch.setattr("backend.api.questions.get_question_by_id", lambda qid: object())
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_question_detail_renders_html(client):
    resp = client.get("/questions/any-id", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert b"Question Detail" in resp.data
