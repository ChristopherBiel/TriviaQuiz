from backend.storage import get_user_store
from backend.models.user import UserModel
from backend.utils.password_utils import hash_password
import secrets
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generate_code(length: int = 6) -> str:
    """Generate a random numeric code of the given length."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


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

    if store.get_by_email(email.strip()):
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


def get_user_by_email(email: str) -> UserModel | None:
    return get_user_store().get_by_email(email)


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
        payload["reset_code"] = updates.get("reset_code")
        payload["reset_expires_at"] = updates.get("reset_expires_at")
    if "verification_token" in updates or "verification_expires_at" in updates:
        payload["verification_token"] = updates.get("verification_token")
        payload["verification_code"] = updates.get("verification_code")
        payload["verification_expires_at"] = updates.get("verification_expires_at")
    if "pending_email" in updates:
        payload["pending_email"] = updates.get("pending_email")
    if "last_login_at" in updates:
        payload["last_login_at"] = updates["last_login_at"]
    if "last_login_ip" in updates:
        payload["last_login_ip"] = updates["last_login_ip"]

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
    code = _generate_code()
    expires = _utcnow() + timedelta(minutes=ttl_minutes)
    return get_user_store().update(user.user_id, {
        "verification_token": token,
        "verification_code": code,
        "verification_expires_at": expires,
    })


def verify_user(token_or_code: str) -> UserModel | None:
    """Verify a user by either a URL token or a 6-digit code."""
    store = get_user_store()

    # Try as token first, then as code
    u = store.get_by_verification_token(token_or_code)
    if not u:
        u = store.get_by_verification_code(token_or_code)
    if not u:
        return None

    if not u.verification_expires_at or u.verification_expires_at <= _utcnow():
        return None

    updates = {
        "is_verified": True,
        "is_approved": True,
        "verification_token": None,
        "verification_code": None,
        "verification_expires_at": None,
    }

    # If there's a pending email change, apply it on verification
    if u.pending_email:
        updates["email"] = u.pending_email
        updates["pending_email"] = None

    return store.update(u.user_id, updates)


def issue_reset_token(user: UserModel, ttl_minutes: int = 15) -> UserModel | None:
    token = secrets.token_urlsafe(16)
    code = _generate_code()
    expires = _utcnow() + timedelta(minutes=ttl_minutes)
    return get_user_store().update(user.user_id, {
        "reset_token": token,
        "reset_code": code,
        "reset_expires_at": expires,
    })


def reset_password(token_or_code: str, new_password: str) -> UserModel | None:
    """Reset password using either a URL token or a 6-digit code."""
    store = get_user_store()

    u = store.get_by_reset_token(token_or_code)
    if not u:
        u = store.get_by_reset_code(token_or_code)
    if not u:
        return None

    if not u.reset_expires_at or u.reset_expires_at <= _utcnow():
        return None

    return store.update(
        u.user_id,
        {
            "password_hash": hash_password(new_password),
            "reset_token": None,
            "reset_code": None,
            "reset_expires_at": None,
        },
    )


def issue_email_change(user: UserModel, new_email: str, ttl_minutes: int = 15) -> UserModel | None:
    """Start an email change flow: store pending email and issue verification."""
    store = get_user_store()

    # Check new email isn't already taken
    if store.get_by_email(new_email.strip()):
        return None

    token = secrets.token_urlsafe(16)
    code = _generate_code()
    expires = _utcnow() + timedelta(minutes=ttl_minutes)

    return store.update(user.user_id, {
        "pending_email": new_email.strip(),
        "verification_token": token,
        "verification_code": code,
        "verification_expires_at": expires,
    })
