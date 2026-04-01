import pytest
from flask import Flask
from backend.api.users import users_bp
from backend.models.user import UserModel


@pytest.fixture
def app(monkeypatch):
    app = Flask(__name__, template_folder="../../templates")
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
            verification_code="123456",
        )
        store[user.username] = user
        return user

    def fake_get_user(username):
        return store.get(username)

    def fake_get_user_by_email(email):
        for u in store.values():
            if u.email == email:
                return u
        return None

    def fake_issue_verification(user, ttl_minutes=15):
        return user

    def fake_verify_user(token_or_code):
        for u in store.values():
            if u.verification_token == token_or_code or u.verification_code == token_or_code:
                u.is_verified = True
                u.is_approved = True
                return u
        return None

    def fake_issue_reset(user, ttl_minutes=15):
        user.reset_token = "reset-tok"
        user.reset_code = "654321"
        return user

    def fake_reset_password(token_or_code, new_password):
        for u in store.values():
            if u.reset_token == token_or_code or u.reset_code == token_or_code:
                return u
        return None

    def fake_issue_email_change(user, new_email, ttl_minutes=15):
        return user

    monkeypatch.setattr("backend.api.users.create_user", fake_create)
    monkeypatch.setattr("backend.api.users.get_user", fake_get_user)
    monkeypatch.setattr("backend.api.users.get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr("backend.api.users.issue_verification", fake_issue_verification)
    monkeypatch.setattr("backend.api.users.verify_user", fake_verify_user)
    monkeypatch.setattr("backend.api.users.issue_reset_token", fake_issue_reset)
    monkeypatch.setattr("backend.api.users.reset_password", fake_reset_password)
    monkeypatch.setattr("backend.api.users.issue_email_change", fake_issue_email_change)
    monkeypatch.setattr("backend.api.users.send_email", lambda to, subject, html, text=None: True)

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


def test_verify_with_code(client):
    client.post("/users/signup", json={"username": "u3", "email": "u3@test.com", "password": "pw"})

    verify = client.post("/users/verify", json={"code": "123456"})
    assert verify.status_code == 200
    assert verify.get_json()["is_verified"] is True


def test_reset_flow(client):
    client.post("/users/signup", json={"username": "u2", "email": "u2@test.com", "password": "pw"})
    req = client.post("/users/request-reset", json={"email": "u2@test.com"})
    assert req.status_code == 200
    reset = client.post("/users/reset", json={"token": "reset-tok", "password": "newpw"})
    assert reset.status_code == 200


def test_reset_with_code(client):
    client.post("/users/signup", json={"username": "u4", "email": "u4@test.com", "password": "pw"})
    client.post("/users/request-reset", json={"email": "u4@test.com"})
    reset = client.post("/users/reset", json={"code": "654321", "password": "newpw"})
    assert reset.status_code == 200


def test_reset_unknown_email_returns_200(client):
    """Password reset for unknown email should still return 200 to prevent enumeration."""
    resp = client.post("/users/request-reset", json={"email": "nobody@test.com"})
    assert resp.status_code == 200


def test_resend_verification(client):
    client.post("/users/signup", json={"username": "u5", "email": "u5@test.com", "password": "pw"})
    resp = client.post("/users/resend-verification", json={"email": "u5@test.com"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"


def test_resend_verification_unknown_email_returns_200(client):
    """Resend for unknown email should still return 200 to prevent enumeration."""
    resp = client.post("/users/resend-verification", json={"email": "nobody@test.com"})
    assert resp.status_code == 200
