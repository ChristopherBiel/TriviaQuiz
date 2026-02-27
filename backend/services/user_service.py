from backend.storage import get_user_store
from backend.models.user import UserModel
from backend.utils.password_utils import hash_password
import secrets
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_user(data: dict, acting_role: str = "admin") -> UserModel | None:
    store = get_user_store()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if acting_role != "admin" and role != "user":
        return None

    if not username or not email or not password:
        return None

    if store.get_by_username(username):
        return None

    user = UserModel(
        username=username.strip(),
        email=email.strip(),
        password_hash=hash_password(password),
        role=role,
        is_verified=data.get("is_verified", False),
        is_approved=data.get("is_approved", False),
    )

    success = store.add(user)
    return user if success else None


def get_user(username: str) -> UserModel | None:
    return get_user_store().get_by_username(username)


def get_user_by_id(user_id: str) -> UserModel | None:
    return get_user_store().get_by_id(user_id)


def list_users(filters: dict | None = None) -> list[UserModel]:
    return get_user_store().list(filters)


def update_user(username: str, updates: dict, acting_role: str, acting_username: str | None = None) -> UserModel | None:
    store = get_user_store()
    existing = store.get_by_username(username)
    if not existing:
        return None

    if acting_role != "admin" and acting_username != username:
        return None

    payload = {}
    if "email" in updates:
        payload["email"] = updates["email"].strip()
    if "password" in updates:
        payload["password_hash"] = hash_password(updates["password"])
    if "role" in updates and acting_role == "admin":
        payload["role"] = updates["role"]
    if "is_verified" in updates and acting_role == "admin":
        payload["is_verified"] = bool(updates["is_verified"])
    if "is_approved" in updates and acting_role == "admin":
        payload["is_approved"] = bool(updates["is_approved"])
    if "username" in updates and (acting_role == "admin" or acting_username == username):
        payload["username"] = updates["username"].strip()
    if "reset_token" in updates or "reset_expires_at" in updates:
        payload["reset_token"] = updates.get("reset_token")
        payload["reset_expires_at"] = updates.get("reset_expires_at")
    if "verification_token" in updates or "verification_expires_at" in updates:
        payload["verification_token"] = updates.get("verification_token")
        payload["verification_expires_at"] = updates.get("verification_expires_at")

    if not payload:
        return None

    return store.update(existing.user_id, payload)


def delete_user(username: str, acting_role: str) -> bool:
    if acting_role != "admin":
        return False
    store = get_user_store()
    existing = store.get_by_username(username)
    if not existing:
        return False
    return store.delete(existing.user_id)


def issue_verification(user: UserModel, ttl_minutes: int = 15) -> UserModel | None:
    token = secrets.token_urlsafe(16)
    expires = _utcnow() + timedelta(minutes=ttl_minutes)
    return get_user_store().update(user.user_id, {"verification_token": token, "verification_expires_at": expires})


def verify_user(token: str) -> UserModel | None:
    users = get_user_store().list()
    for u in users:
        if u.verification_token == token and u.verification_expires_at and u.verification_expires_at > _utcnow():
            return get_user_store().update(
                u.user_id,
                {"is_verified": True, "verification_token": None, "verification_expires_at": None},
            )
    return None


def issue_reset_token(user: UserModel, ttl_minutes: int = 15) -> UserModel | None:
    token = secrets.token_urlsafe(16)
    expires = _utcnow() + timedelta(minutes=ttl_minutes)
    return get_user_store().update(user.user_id, {"reset_token": token, "reset_expires_at": expires})


def reset_password(token: str, new_password: str) -> UserModel | None:
    users = get_user_store().list()
    for u in users:
        if u.reset_token == token and u.reset_expires_at and u.reset_expires_at > _utcnow():
            return get_user_store().update(
                u.user_id,
                {
                    "password_hash": hash_password(new_password),
                    "reset_token": None,
                    "reset_expires_at": None,
                },
            )
    return None
