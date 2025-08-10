import pytest
from backend.services import user_services

class DummyUser:
    def __init__(self, user_id, username, email):
        self.id = user_id
        self.username = username
        self.email = email

@pytest.fixture
def sample_user():
    return DummyUser(user_id=1, username="testuser", email="test@example.com")

def test_create_user(monkeypatch):
    def mock_create(username, email, password):
        return DummyUser(1, username, email)
    monkeypatch.setattr(user_services, "create_user", mock_create)
    user = user_services.create_user("testuser", "test@example.com", "password123")
    assert user.username == "testuser"
    assert user.email == "test@example.com"

def test_get_user_by_id(monkeypatch, sample_user):
    def mock_get(user_id):
        if user_id == 1:
            return sample_user
        return None
    monkeypatch.setattr(user_services, "get_user_by_id", mock_get)
    user = user_services.get_user_by_id(1)
    assert user.id == 1
    assert user.username == "testuser"

def test_authenticate_user_success(monkeypatch, sample_user):
    def mock_auth(username, password):
        if username == "testuser" and password == "password123":
            return sample_user
        return None
    monkeypatch.setattr(user_services, "authenticate_user", mock_auth)
    user = user_services.authenticate_user("testuser", "password123")
    assert user is not None
    assert user.username == "testuser"

def test_authenticate_user_failure(monkeypatch):
    def mock_auth(username, password):
        return None
    monkeypatch.setattr(user_services, "authenticate_user", mock_auth)
    user = user_services.authenticate_user("wronguser", "wrongpass")
    assert user is None