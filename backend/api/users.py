import logging

from flask import Blueprint, request, jsonify, session, render_template
from backend.services.user_service import (
    create_user,
    get_user,
    get_user_by_email,
    list_users,
    update_user,
    delete_user,
    issue_verification,
    verify_user,
    issue_reset_token,
    reset_password,
    issue_email_change,
)
from backend.utils.email_stub import send_email
from backend.utils.rate_limit import email_send_limiter, code_attempt_limiter, signup_limiter
from backend.core.settings import get_settings

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__, url_prefix="/users")

_SENSITIVE_FIELDS = {"password_hash", "reset_token", "reset_code", "reset_expires_at",
                     "verification_token", "verification_code", "verification_expires_at",
                     "pending_email"}


def _safe_dump(user) -> dict:
    return user.model_dump(mode="json", exclude=_SENSITIVE_FIELDS)


def _require_admin():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403
    return None


def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


def _send_verification_email(user) -> bool:
    """Send verification email with both link and code."""
    settings = get_settings()
    base = settings.app_base_url.rstrip("/")
    link = f"{base}/verify_email?token={user.verification_token}"

    html = render_template("email/verify.html",
                           code=user.verification_code,
                           link=link,
                           ttl_minutes=15)
    text = (
        f"Your verification code is: {user.verification_code}\n\n"
        f"Or click this link to verify: {link}\n\n"
        f"This code expires in 15 minutes."
    )
    return send_email(user.email, "Verify your TriviaQuiz account", html, text)


def _send_reset_email(user) -> bool:
    """Send password reset email with both link and code."""
    settings = get_settings()
    base = settings.app_base_url.rstrip("/")
    link = f"{base}/reset_password?token={user.reset_token}"

    html = render_template("email/reset.html",
                           code=user.reset_code,
                           link=link,
                           ttl_minutes=15)
    text = (
        f"Your password reset code is: {user.reset_code}\n\n"
        f"Or click this link to reset your password: {link}\n\n"
        f"This code expires in 15 minutes."
    )
    return send_email(user.email, "Reset your TriviaQuiz password", html, text)


# ── Public endpoints ──────────────────────────────────────────────────


@users_bp.route("/signup", methods=["POST"])
def users_signup():
    data = request.get_json(silent=True) or {}

    ip = _client_ip()
    if not signup_limiter.check_and_record(f"signup:{ip}"):
        return jsonify({"status": "error", "message": "Too many signup attempts. Please try again later."}), 429

    create_data = {
        "username": data.get("username"),
        "email": data.get("email"),
        "password": data.get("password"),
    }

    user = create_user(create_data, acting_role="user")
    if not user:
        return jsonify({"status": "error", "message": "Signup failed. Username or email may already be taken."}), 400

    issued = issue_verification(user)
    if issued:
        email_key = f"verify:{user.email}"
        if email_send_limiter.check_and_record(email_key):
            _send_verification_email(issued)

    return jsonify({"status": "success", "message": "Signup successful. Check your email to verify your account."}), 201


@users_bp.route("/verify", methods=["POST"])
def users_verify():
    data = request.get_json(silent=True) or {}
    token_or_code = data.get("token") or data.get("code")
    if not token_or_code:
        return jsonify({"error": "Missing token or code"}), 400

    ip = _client_ip()
    if not code_attempt_limiter.check_and_record(f"verify:{ip}"):
        return jsonify({"error": "Too many attempts. Please try again later."}), 429

    user = verify_user(token_or_code)
    if not user:
        return jsonify({"error": "Invalid or expired token/code"}), 400
    return jsonify(_safe_dump(user)), 200


@users_bp.route("/resend-verification", methods=["POST"])
def users_resend_verification():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "Missing email"}), 400

    email_key = f"verify:{email}"
    if not email_send_limiter.check_and_record(email_key):
        return jsonify({"error": "Too many requests. Please try again later."}), 429

    user = get_user_by_email(email)
    if user and not user.is_verified:
        issued = issue_verification(user)
        if issued:
            _send_verification_email(issued)

    # Always return success to avoid leaking whether the email exists
    return jsonify({"status": "success", "message": "If an unverified account exists with that email, a verification email has been sent."}), 200


@users_bp.route("/request-reset", methods=["POST"])
def users_request_reset():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "Missing email"}), 400

    email_key = f"reset:{email}"
    if not email_send_limiter.check_and_record(email_key):
        return jsonify({"error": "Too many requests. Please try again later."}), 429

    user = get_user_by_email(email)
    if user:
        updated = issue_reset_token(user)
        if updated:
            _send_reset_email(updated)
    else:
        logger.info("Password reset requested for unknown email: %s", email)

    # Always return the same response to avoid leaking whether the email exists
    return jsonify({"status": "reset_sent", "message": "If an account exists with that email, a reset email has been sent."}), 200


@users_bp.route("/reset", methods=["POST"])
def users_reset():
    data = request.get_json(silent=True) or {}
    token_or_code = data.get("token") or data.get("code")
    new_password = data.get("password")
    if not token_or_code or not new_password:
        return jsonify({"error": "Missing token/code or password"}), 400

    ip = _client_ip()
    if not code_attempt_limiter.check_and_record(f"reset:{ip}"):
        return jsonify({"error": "Too many attempts. Please try again later."}), 429

    user = reset_password(token_or_code, new_password)
    if not user:
        return jsonify({"error": "Invalid or expired token/code"}), 400
    return jsonify({"status": "password_updated"}), 200


@users_bp.route("/me/password", methods=["POST"])
def users_change_password():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    new_password = data.get("password")
    if not new_password:
        return jsonify({"error": "Missing password"}), 400
    updated = update_user(session.get("username"), {"password": new_password}, acting_role=session.get("role"), acting_username=session.get("username"))
    if not updated:
        return jsonify({"error": "Failed to update password"}), 400
    return jsonify({"status": "password_updated"}), 200


@users_bp.route("/me/email", methods=["POST"])
def users_change_email():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    new_email = data.get("email")
    if not new_email:
        return jsonify({"error": "Missing email"}), 400

    user = get_user(session.get("username"))
    if not user:
        return jsonify({"error": "User not found"}), 404

    email_key = f"verify:{new_email}"
    if not email_send_limiter.check_and_record(email_key):
        return jsonify({"error": "Too many requests. Please try again later."}), 429

    issued = issue_email_change(user, new_email)
    if not issued:
        return jsonify({"error": "Email change failed. The email may already be in use."}), 400

    _send_verification_email(issued)
    return jsonify({"status": "success", "message": "Verification email sent to your new address. Please verify to complete the change."}), 200


# ── Admin endpoints ───────────────────────────────────────────────────


@users_bp.route("/", methods=["GET"])
def users_list():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    users = list_users()
    return jsonify([_safe_dump(u) for u in users]), 200


@users_bp.route("/<username>", methods=["GET"])
def users_get(username):
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    user = get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(_safe_dump(user)), 200


@users_bp.route("/", methods=["POST"])
def users_create():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    user = create_user(data, acting_role=session.get("role"))
    if not user:
        return jsonify({"error": "Failed to create user"}), 400
    return jsonify(_safe_dump(user)), 201


@users_bp.route("/<username>", methods=["PUT"])
def users_update(username):
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    updated = update_user(username, data, acting_role=session.get("role"), acting_username=session.get("username"))
    if not updated:
        return jsonify({"error": "User not found or no changes"}), 404
    return jsonify(_safe_dump(updated)), 200


@users_bp.route("/<username>", methods=["DELETE"])
def users_delete(username):
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    success = delete_user(username, acting_role=session.get("role"))
    if not success:
        return jsonify({"error": "User not found"}), 404
    return "", 204
