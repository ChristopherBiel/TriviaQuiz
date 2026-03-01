import pytest

from backend.main import create_app


@pytest.fixture
def app(monkeypatch):
    app = create_app()
    app.testing = True
    monkeypatch.setattr("backend.api.users.delete_user", lambda username, acting_role: True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _login_admin(client):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["role"] = "admin"


def test_delete_user_uses_api_route(client):
    _login_admin(client)
    resp = client.delete("/users/some-user")
    assert resp.status_code == 204
