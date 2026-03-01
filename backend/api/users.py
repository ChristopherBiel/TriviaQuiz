from flask import Blueprint, request, jsonify, session
from backend.services.user_service import (
    create_user,
    get_user,
    list_users,
    update_user,
    delete_user,
    issue_verification,
    verify_user,
    issue_reset_token,
    reset_password,
)
from backend.utils.email_stub import send_email
from backend.core.settings import get_settings

users_bp = Blueprint("users", __name__, url_prefix="/users")


def _require_admin():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403
    return None


@users_bp.route("/signup", methods=["POST"])
def users_signup():
    data = request.get_json(silent=True) or {}
    settings = get_settings()

    referral_code = data.get("referral_code", "")
    create_data = {
        "username": data.get("username"),
        "email": data.get("email"),
        "password": data.get("password"),
    }

    if settings.signup_referral_code:
        if referral_code != settings.signup_referral_code:
            return jsonify({"status": "error", "message": "Invalid referral code"}), 403
        create_data["is_verified"] = True
        create_data["is_approved"] = True

    user = create_user(create_data, acting_role="user")
    if not user:
        return jsonify({"status": "error", "message": "Signup failed. Username may already be taken."}), 400

    if not settings.signup_referral_code:
        issued = issue_verification(user)
        if issued:
            send_email(user.email, "Verify your account", f"Token: {issued.verification_token}")
        return jsonify({"status": "success", "message": "Signup successful. Check your email to verify your account."}), 201

    return jsonify({"status": "success", "message": "Signup successful. You can now log in."}), 201


@users_bp.route("/verify", methods=["POST"])
def users_verify():
    token = (request.get_json(silent=True) or {}).get("token")
    if not token:
        return jsonify({"error": "Missing token"}), 400
    user = verify_user(token)
    if not user:
        return jsonify({"error": "Invalid or expired token"}), 400
    return jsonify(user.model_dump(mode="json")), 200


@users_bp.route("/request-reset", methods=["POST"])
def users_request_reset():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    if not username:
        return jsonify({"error": "Missing username"}), 400
    user = get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    updated = issue_reset_token(user)
    if updated:
        send_email(user.email, "Reset your password", f"Token: {updated.reset_token}")
    return jsonify({"status": "reset_sent"}), 200


@users_bp.route("/reset", methods=["POST"])
def users_reset():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    new_password = data.get("password")
    if not token or not new_password:
        return jsonify({"error": "Missing token or password"}), 400
    user = reset_password(token, new_password)
    if not user:
        return jsonify({"error": "Invalid or expired token"}), 400
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


@users_bp.route("/", methods=["GET"])
def users_list():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    users = list_users()
    return jsonify([u.model_dump(mode="json") for u in users]), 200


@users_bp.route("/<username>", methods=["GET"])
def users_get(username):
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    user = get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.model_dump(mode="json")), 200


@users_bp.route("/", methods=["POST"])
def users_create():
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    user = create_user(data, acting_role=session.get("role"))
    if not user:
        return jsonify({"error": "Failed to create user"}), 400
    return jsonify(user.model_dump(mode="json")), 201


@users_bp.route("/<username>", methods=["PUT"])
def users_update(username):
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    data = request.get_json(silent=True) or {}
    updated = update_user(username, data, acting_role=session.get("role"), acting_username=session.get("username"))
    if not updated:
        return jsonify({"error": "User not found or no changes"}), 404
    return jsonify(updated.model_dump(mode="json")), 200


@users_bp.route("/<username>", methods=["DELETE"])
def users_delete(username):
    auth_error = _require_admin()
    if auth_error:
        return auth_error
    success = delete_user(username, acting_role=session.get("role"))
    if not success:
        return jsonify({"error": "User not found"}), 404
    return "", 204
