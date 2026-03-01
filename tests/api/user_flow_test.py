import pytest
from flask import Flask
from backend.api.users import users_bp
from backend.models.user import UserModel


@pytest.fixture
def app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test"

    # simple in-memory store
    store = {}

    def fake_create(data, acting_role="user"):
        user = UserModel(
            username=data["username"],
            email=data["email"],
            password_hash="hashed",
            role="user",
            is_verified=False,
            is_approved=False,
            verification_token="tok",
        )
        store[user.username] = user
        return user

    def fake_get_user(username):
        return store.get(username)

    def fake_issue_verification(user):
        return user

    def fake_verify_user(token):
        for u in store.values():
            if u.verification_token == token:
                u.is_verified = True
                return u
        return None

    def fake_issue_reset(user):
        user.reset_token = "reset"
        return user

    def fake_reset_password(token, new_password):
        for u in store.values():
            if u.reset_token == token:
                return u
        return None

    monkeypatch.setattr("backend.api.users.create_user", fake_create)
    monkeypatch.setattr("backend.api.users.get_user", fake_get_user)
    monkeypatch.setattr("backend.api.users.issue_verification", fake_issue_verification)
    monkeypatch.setattr("backend.api.users.verify_user", fake_verify_user)
    monkeypatch.setattr("backend.api.users.issue_reset_token", fake_issue_reset)
    monkeypatch.setattr("backend.api.users.reset_password", fake_reset_password)
    monkeypatch.setattr("backend.api.users.send_email", lambda to, subject, body: None)

    app.register_blueprint(users_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_signup_and_verify_flow(client):
    resp = client.post("/users/signup", json={"username": "u", "email": "u@test.com", "password": "pw"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "success"

    verify = client.post("/users/verify", json={"token": "tok"})
    assert verify.status_code == 200
    assert verify.get_json()["is_verified"] is True


def test_reset_flow(client):
    client.post("/users/signup", json={"username": "u2", "email": "u2@test.com", "password": "pw"})
    req = client.post("/users/request-reset", json={"username": "u2"})
    assert req.status_code == 200
    reset = client.post("/users/reset", json={"token": "reset", "password": "newpw"})
    assert reset.status_code == 200
