# tests for user_service.py

"""
Unit tests for all functions in user_service.py.
- Covers all CRUD operations and auth workflows.
- Mocks store interactions via monkeypatch to isolate service logic.
"""

import pytest
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from unittest.mock import MagicMock, call
from types import SimpleNamespace

from backend.services.user_service import (
    create_user,
    get_user,
    get_user_by_id,
    list_users,
    update_user,
    delete_user,
    issue_verification,
    verify_user,
    issue_reset_token,
    reset_password,
)
from backend.models.user import UserModel


@pytest.fixture
def sample_user():
    return UserModel(
        username="alice",
        email="alice@example.com",
        password_hash="hashed",
        role="user",
        is_verified=True,
        is_approved=True,
    )


@pytest.fixture
def mock_store(monkeypatch):
    store = MagicMock()
    store.get_by_username.return_value = None
    store.get_by_id.return_value = None
    store.list.return_value = []
    store.add.return_value = True
    store.update.return_value = None
    store.delete.return_value = False
    monkeypatch.setattr("backend.services.user_service.get_user_store", lambda: store)
    return store


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

def test_create_user_success(mock_store):
    mock_store.get_by_username.return_value = None
    mock_store.add.return_value = True
    result = create_user({"username": "bob", "email": "bob@example.com", "password": "pw"}, acting_role="admin")
    assert result is not None
    assert result.username == "bob"
    assert result.email == "bob@example.com"
    mock_store.add.assert_called_once()


def test_create_user_strips_whitespace(mock_store):
    mock_store.add.return_value = True
    result = create_user({"username": "  bob  ", "email": "  bob@example.com  ", "password": "pw"}, acting_role="admin")
    assert result.username == "bob"
    assert result.email == "bob@example.com"


def test_create_user_missing_fields_returns_none(mock_store):
    assert create_user({"username": "bob", "email": "bob@example.com"}, acting_role="admin") is None
    assert create_user({"username": "bob", "password": "pw"}, acting_role="admin") is None
    assert create_user({"email": "bob@example.com", "password": "pw"}, acting_role="admin") is None
    mock_store.add.assert_not_called()


def test_create_user_duplicate_username_returns_none(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    result = create_user({"username": "alice", "email": "x@x.com", "password": "pw"}, acting_role="admin")
    assert result is None
    mock_store.add.assert_not_called()


def test_create_user_store_failure_returns_none(mock_store):
    mock_store.add.return_value = False
    result = create_user({"username": "bob", "email": "bob@example.com", "password": "pw"})
    assert result is None


def test_create_user_non_admin_cannot_create_admin_role(mock_store):
    mock_store.add.return_value = True
    result = create_user({"username": "bob", "email": "bob@example.com", "password": "pw", "role": "admin"}, acting_role="user")
    assert result is None
    mock_store.add.assert_not_called()


def test_create_user_admin_can_create_admin_role(mock_store):
    mock_store.add.return_value = True
    result = create_user({"username": "bob", "email": "bob@example.com", "password": "pw", "role": "admin"}, acting_role="admin")
    assert result is not None
    assert result.role == "admin"


def test_create_user_default_role_is_user(mock_store):
    mock_store.add.return_value = True
    result = create_user({"username": "bob", "email": "bob@example.com", "password": "pw"})
    assert result.role == "user"


# ---------------------------------------------------------------------------
# get_user / get_user_by_id
# ---------------------------------------------------------------------------

def test_get_user_found(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    assert get_user("alice") is sample_user
    mock_store.get_by_username.assert_called_once_with("alice")


def test_get_user_not_found(mock_store):
    assert get_user("nobody") is None


def test_get_user_by_id_found(mock_store, sample_user):
    mock_store.get_by_id.return_value = sample_user
    assert get_user_by_id(sample_user.user_id) is sample_user


def test_get_user_by_id_not_found(mock_store):
    assert get_user_by_id("missing-id") is None


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

def test_list_users_returns_all(mock_store, sample_user):
    mock_store.list.return_value = [sample_user]
    result = list_users()
    assert result == [sample_user]
    mock_store.list.assert_called_once_with(None)


def test_list_users_passes_filters(mock_store):
    mock_store.list.return_value = []
    list_users(filters={"role": "admin"})
    mock_store.list.assert_called_once_with({"role": "admin"})


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

def test_update_user_not_found_returns_none(mock_store):
    mock_store.get_by_username.return_value = None
    assert update_user("nobody", {"email": "x@x.com"}, acting_role="admin") is None
    mock_store.update.assert_not_called()


def test_update_user_non_admin_cannot_update_other(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    result = update_user("alice", {"email": "x@x.com"}, acting_role="user", acting_username="bob")
    assert result is None
    mock_store.update.assert_not_called()


def test_update_user_user_can_update_self(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    mock_store.update.return_value = sample_user.model_copy(update={"email": "new@example.com"})
    result = update_user("alice", {"email": "new@example.com"}, acting_role="user", acting_username="alice")
    assert result is not None
    mock_store.update.assert_called_once_with(sample_user.user_id, {"email": "new@example.com"})


def test_update_user_admin_can_set_role(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    mock_store.update.return_value = sample_user.model_copy(update={"role": "admin"})
    update_user("alice", {"role": "admin"}, acting_role="admin")
    args = mock_store.update.call_args[0][1]
    assert args["role"] == "admin"


def test_update_user_non_admin_cannot_set_role(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    mock_store.update.return_value = sample_user
    result = update_user("alice", {"role": "admin"}, acting_role="user", acting_username="alice")
    # role key should NOT be in the payload sent to store
    assert result is None  # no other allowed fields → empty payload → None


def test_update_user_admin_can_set_is_verified_and_is_approved(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    mock_store.update.return_value = sample_user
    update_user("alice", {"is_verified": True, "is_approved": True}, acting_role="admin")
    args = mock_store.update.call_args[0][1]
    assert args["is_verified"] is True
    assert args["is_approved"] is True


def test_update_user_non_admin_cannot_set_is_verified(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    result = update_user("alice", {"is_verified": True}, acting_role="user", acting_username="alice")
    assert result is None  # field stripped → empty payload


def test_update_user_password_is_hashed(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    mock_store.update.return_value = sample_user
    update_user("alice", {"password": "newpassword"}, acting_role="admin")
    args = mock_store.update.call_args[0][1]
    assert "password_hash" in args
    assert args["password_hash"] != "newpassword"  # was hashed


def test_update_user_empty_payload_returns_none(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    # "unknown_field" is not in the allowed payload keys
    result = update_user("alice", {"unknown_field": "x"}, acting_role="admin")
    assert result is None
    mock_store.update.assert_not_called()


def test_update_user_reset_token_fields(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    mock_store.update.return_value = sample_user
    expires = _utcnow() + timedelta(minutes=15)
    update_user("alice", {"reset_token": "tok", "reset_expires_at": expires}, acting_role="admin")
    args = mock_store.update.call_args[0][1]
    assert args["reset_token"] == "tok"
    assert args["reset_expires_at"] == expires


def test_update_user_verification_token_fields(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    mock_store.update.return_value = sample_user
    expires = _utcnow() + timedelta(minutes=15)
    update_user("alice", {"verification_token": "vtok", "verification_expires_at": expires}, acting_role="admin")
    args = mock_store.update.call_args[0][1]
    assert args["verification_token"] == "vtok"


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

def test_delete_user_non_admin_blocked(mock_store):
    assert delete_user("alice", acting_role="user") is False
    mock_store.get_by_username.assert_not_called()


def test_delete_user_not_found(mock_store):
    mock_store.get_by_username.return_value = None
    assert delete_user("nobody", acting_role="admin") is False
    mock_store.delete.assert_not_called()


def test_delete_user_success(mock_store, sample_user):
    mock_store.get_by_username.return_value = sample_user
    mock_store.delete.return_value = True
    assert delete_user("alice", acting_role="admin") is True
    mock_store.delete.assert_called_once_with(sample_user.user_id)


# ---------------------------------------------------------------------------
# issue_verification / verify_user
# ---------------------------------------------------------------------------

def test_issue_verification_calls_store_update(mock_store, sample_user):
    mock_store.update.return_value = sample_user
    issue_verification(sample_user)
    args = mock_store.update.call_args[0]
    assert args[0] == sample_user.user_id
    payload = args[1]
    assert "verification_token" in payload
    assert payload["verification_token"] is not None
    assert "verification_expires_at" in payload
    assert payload["verification_expires_at"] > _utcnow()


def test_verify_user_valid_token(mock_store, sample_user):
    user_with_token = sample_user.model_copy(update={
        "verification_token": "good-token",
        "verification_expires_at": _utcnow() + timedelta(minutes=10),
        "is_verified": False,
    })
    mock_store.list.return_value = [user_with_token]
    mock_store.update.return_value = user_with_token.model_copy(update={"is_verified": True})

    result = verify_user("good-token")
    assert result is not None
    mock_store.update.assert_called_once_with(
        user_with_token.user_id,
        {"is_verified": True, "verification_token": None, "verification_expires_at": None},
    )


def test_verify_user_expired_token_returns_none(mock_store, sample_user):
    user_with_expired = sample_user.model_copy(update={
        "verification_token": "old-token",
        "verification_expires_at": _utcnow() - timedelta(minutes=1),
    })
    mock_store.list.return_value = [user_with_expired]
    assert verify_user("old-token") is None
    mock_store.update.assert_not_called()


def test_verify_user_wrong_token_returns_none(mock_store, sample_user):
    user_with_token = sample_user.model_copy(update={
        "verification_token": "right-token",
        "verification_expires_at": _utcnow() + timedelta(minutes=10),
    })
    mock_store.list.return_value = [user_with_token]
    assert verify_user("wrong-token") is None
    mock_store.update.assert_not_called()


def test_verify_user_no_users_returns_none(mock_store):
    mock_store.list.return_value = []
    assert verify_user("any-token") is None


# ---------------------------------------------------------------------------
# issue_reset_token / reset_password
# ---------------------------------------------------------------------------

def test_issue_reset_token_calls_store_update(mock_store, sample_user):
    mock_store.update.return_value = sample_user
    issue_reset_token(sample_user)
    args = mock_store.update.call_args[0]
    assert args[0] == sample_user.user_id
    payload = args[1]
    assert "reset_token" in payload
    assert payload["reset_token"] is not None
    assert "reset_expires_at" in payload
    assert payload["reset_expires_at"] > _utcnow()


def test_reset_password_valid_token(mock_store, sample_user):
    user_with_token = sample_user.model_copy(update={
        "reset_token": "reset-tok",
        "reset_expires_at": _utcnow() + timedelta(minutes=10),
    })
    mock_store.list.return_value = [user_with_token]
    mock_store.update.return_value = user_with_token

    result = reset_password("reset-tok", "newpassword")
    assert result is not None
    args = mock_store.update.call_args[0][1]
    assert "password_hash" in args
    assert args["password_hash"] != "newpassword"
    assert args["reset_token"] is None
    assert args["reset_expires_at"] is None


def test_reset_password_expired_token_returns_none(mock_store, sample_user):
    user_with_expired = sample_user.model_copy(update={
        "reset_token": "reset-tok",
        "reset_expires_at": _utcnow() - timedelta(minutes=1),
    })
    mock_store.list.return_value = [user_with_expired]
    assert reset_password("reset-tok", "newpw") is None
    mock_store.update.assert_not_called()


def test_reset_password_wrong_token_returns_none(mock_store, sample_user):
    user_with_token = sample_user.model_copy(update={
        "reset_token": "right-tok",
        "reset_expires_at": _utcnow() + timedelta(minutes=10),
    })
    mock_store.list.return_value = [user_with_token]
    assert reset_password("wrong-tok", "newpw") is None
    mock_store.update.assert_not_called()
