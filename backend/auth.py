from datetime import datetime
from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template
from markupsafe import escape
import re

from backend.services.user_service import (
    create_user,
    get_user,
    update_user,
    delete_user,
)
from backend.utils.password_utils import hash_password, verify_password
from backend.utils.email_stub import send_email

auth_bp = Blueprint("auth", __name__)
    
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    # Accept data from HTML form and sanitize it
    username = escape(request.form.get("username", "").strip())
    email = escape(request.form.get("email", "").strip())
    password = request.form.get("password", "")

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    if not re.match(r"^[\\w.@+-]+$", username):
        return jsonify({"status": "error", "message": "Username contains invalid characters"}), 400

    if not re.match(r"^[^@]+@[^@]+\\.[^@]+$", email):
        return jsonify({"status": "error", "message": "Invalid email format"}), 400

    user = create_user({"username": username, "email": email, "password": password}, acting_role="user")
    if not user:
        return jsonify({"status": "error", "message": "Signup failed"}), 400
    if user.verification_token:
        send_email(user.email, "Verify your account", f"Token: {user.verification_token}")
    return jsonify({"status": "success", "message": "Signup successful, please verify your email."}), 201




@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    # Try form data first
    username = request.form.get("username")
    password = request.form.get("password")

    # Fallback to JSON if form data is empty
    if not username or not password:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Missing login data"}), 400
        username = data.get("username")
        password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    user = get_user(username)
    if not user or not verify_password(password, user.password_hash):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_verified:
        return jsonify({"error": "Email verification required"}), 403

    if not user.is_approved:
        return jsonify({"error": "Admin approval required"}), 403

    update_user(user.username, {"last_login_at": datetime.utcnow(), "last_login_ip": request.remote_addr}, acting_role="admin")

    # Set session variables
    session["logged_in"] = True
    session["username"] = user.username
    session["email"] = user.email
    session["role"] = user.role
    session["is_admin"] = user.role == "admin"
    return redirect("/")


@auth_bp.route("/approve_user", methods=["GET"])
def approve_user():
    return render_template("approve_user.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("routes.serve_frontend"))

@auth_bp.route("/reset_password")
def reset_password_page():
    return render_template("reset_password.html")

@auth_bp.route("/verify_email")
def verify_email_page():
    return render_template("verify_email.html")

def get_all_users():
    """Fetch all users."""
    try:
        from backend.services.user_service import list_users
        return [u.model_dump(mode="json") for u in list_users()]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

def edit_user(user_id, action):
    """Edit user details."""
    try:
        if action == "approve":
            return bool(update_user(user_id, {"is_approved": True}, acting_role="admin"))
        elif action == "reject":
            return bool(update_user(user_id, {"is_approved": False}, acting_role="admin"))
        elif action == "make_admin":
            return bool(update_user(user_id, {"role": "admin"}, acting_role="admin"))
        elif action == "delete":
            return delete_user(user_id, acting_role="admin")
        else:
            return False
    except Exception as e:
        print(f"Error editing user: {e}")
        return False
