from backend.db.userdb import (
    add_user_to_db,
    get_user_by_username_db,
    get_user_by_id_db,
    get_all_users_db,
    update_user_in_db,
    delete_user_from_db,
)
from backend.models.user import UserModel
from backend.utils.password_utils import hash_password
import secrets
from datetime import datetime, timedelta


def create_user(data: dict, acting_role: str = "admin") -> UserModel | None:
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if acting_role != "admin" and role != "user":
        return None

    if not username or not email or not password:
        return None

    if get_user_by_username_db(username):
        return None

    user = UserModel(
        username=username.strip(),
        email=email.strip(),
        password_hash=hash_password(password),
        role=role,
        is_verified=data.get("is_verified", False),
        is_approved=data.get("is_approved", False),
    )

    success = add_user_to_db(user)
    return user if success else None


def get_user(username: str) -> UserModel | None:
    return get_user_by_username_db(username)


def get_user_by_id(user_id: str) -> UserModel | None:
    return get_user_by_id_db(user_id)


def list_users(filters: dict | None = None) -> list[UserModel]:
    return get_all_users_db(filters)


def update_user(username: str, updates: dict, acting_role: str, acting_username: str | None = None) -> UserModel | None:
    existing = get_user_by_username_db(username)
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

    return update_user_in_db(existing.user_id, payload)


def delete_user(username: str, acting_role: str) -> bool:
    if acting_role != "admin":
        return False
    existing = get_user_by_username_db(username)
    if not existing:
        return False
    return delete_user_from_db(existing.user_id)


def issue_verification(user: UserModel, ttl_minutes: int = 15) -> UserModel | None:
    token = secrets.token_urlsafe(16)
    expires = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    return update_user_in_db(user.user_id, {"verification_token": token, "verification_expires_at": expires})


def verify_user(token: str) -> UserModel | None:
    users = get_all_users_db()
    for u in users:
        if u.verification_token == token and u.verification_expires_at and u.verification_expires_at > datetime.utcnow():
            return update_user_in_db(u.user_id, {"is_verified": True, "verification_token": None, "verification_expires_at": None})
    return None


def issue_reset_token(user: UserModel, ttl_minutes: int = 15) -> UserModel | None:
    token = secrets.token_urlsafe(16)
    expires = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    return update_user_in_db(user.user_id, {"reset_token": token, "reset_expires_at": expires})


def reset_password(token: str, new_password: str) -> UserModel | None:
    users = get_all_users_db()
    for u in users:
        if u.reset_token == token and u.reset_expires_at and u.reset_expires_at > datetime.utcnow():
            return update_user_in_db(u.user_id, {"password_hash": hash_password(new_password), "reset_token": None, "reset_expires_at": None})
    return None
