from flask import Blueprint, request, jsonify, session
from backend.services.user_service import (
    get_user_by_username,
    create_user,
    update_user,
    delete_user,
    get_all_users
)

users_bp = Blueprint("users", __name__, url_prefix="/users")

@users_bp.route("/", methods=["GET"])
def list_users():
    """List all users."""
    if not session.get("logged_in") or not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    
    users = get_all_users()
    return jsonify(users), 200

@users_bp.route("/<username>", methods=["GET"])
def get_user(username):
    """Get a specific user by username."""
    if not session.get("logged_in") or not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    
    user = get_user_by_username(username)
    if user:
        return jsonify(user), 200
    return jsonify({"error": "User not found"}), 404

@users_bp.route("/", methods=["POST"])
def create_new_user():
    """Create a new user."""
    if not session.get("logged_in") or not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    try:
        new_user = create_user(data)
        return jsonify(new_user), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
@users_bp.route("/<username>", methods=["PUT"])
def update_existing_user(username):
    """Update an existing user."""
    if not session.get("logged_in") or not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    
    updates = request.get_json()
    if not updates:
        return jsonify({"error": "Missing update data"}), 400

    try:
        updated_user = update_user(username, updates)
        if updated_user:
            return jsonify(updated_user), 200
        return jsonify({"error": "User not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
@users_bp.route("/<username>", methods=["DELETE"])
def delete_existing_user(username):
    """Delete a user."""
    if not session.get("logged_in") or not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    
    success = delete_user(username)
    if success:
        return '', 204
    return jsonify({"error": "User not found"}), 404

@users_bp.route("/me", methods=["GET"])
def get_current_user():
    """Get the currently logged-in user's information."""
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    
    username = session.get("username")
    user = get_user_by_username(username)
    
    if user:
        return jsonify(user), 200
    return jsonify({"error": "User not found"}), 404

@users_bp.route("/me", methods=["PUT"])
def update_current_user():
    """Update the currently logged-in user's information."""
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    
    username = session.get("username")
    updates = request.get_json()
    
    if not updates:
        return jsonify({"error": "Missing update data"}), 400

    try:
        updated_user = update_user(username, updates)
        if updated_user:
            return jsonify(updated_user), 200
        return jsonify({"error": "User not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
@users_bp.route("/me", methods=["DELETE"])
def delete_current_user():
    """Delete the currently logged-in user."""
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    
    username = session.get("username")
    success = delete_user(username)
    
    if success:
        session.clear()
        return '', 204
    return jsonify({"error": "User not found"}), 404

