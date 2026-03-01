import pytest

from backend.main import create_app


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/random-question"),
        ("get", "/get-questions"),
        ("get", "/question-metadata"),
        ("post", "/add-question"),
        ("post", "/approve-question/any-id/any-topic"),
        ("post", "/reject-question/any-id/any-topic"),
        ("delete", "/delete-question/any-id/any-topic"),
        ("get", "/question/any-id"),
        ("get", "/questions/any-id/view"),
    ],
)
def test_legacy_question_routes_removed(client, method, path):
    resp = getattr(client, method)(path)
    assert resp.status_code == 404
