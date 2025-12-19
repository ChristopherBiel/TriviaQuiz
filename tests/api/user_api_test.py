import pytest
from flask import Flask
from unittest.mock import MagicMock

from backend.api.users import users_bp
from backend.models.user import UserModel


@pytest.fixture
def app():
    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(users_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login_admin(client):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["role"] = "admin"


def test_users_list_auth_required(client):
    resp = client.get("/users/")
    assert resp.status_code == 403


def test_users_list(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("backend.api.users.list_users", lambda: [UserModel(username="u", email="u@test.com", password_hash="x")])
    resp = client.get("/users/")
    assert resp.status_code == 200
    assert resp.get_json()[0]["username"] == "u"


def test_users_get_not_found(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("backend.api.users.get_user", lambda username: None)
    resp = client.get("/users/missing")
    assert resp.status_code == 404


def test_users_create(client, monkeypatch):
    login_admin(client)
    created = UserModel(username="u", email="u@test.com", password_hash="x")
    monkeypatch.setattr("backend.api.users.create_user", lambda data, acting_role: created)
    resp = client.post("/users/", json={"username": "u", "email": "u@test.com", "password": "pw"})
    assert resp.status_code == 201
    assert resp.get_json()["username"] == "u"


def test_users_update(client, monkeypatch):
    login_admin(client)
    updated = UserModel(username="u", email="new@test.com", password_hash="x")
    monkeypatch.setattr("backend.api.users.update_user", lambda username, data, acting_role, acting_username: updated)
    resp = client.put("/users/u", json={"email": "new@test.com"})
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "new@test.com"


def test_users_delete(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("backend.api.users.delete_user", lambda username, acting_role: True)
    resp = client.delete("/users/u")
    assert resp.status_code == 204
