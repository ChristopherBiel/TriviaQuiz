from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from backend.auth import auth_bp, get_all_users  # Import authentication blueprint

routes_bp = Blueprint("routes", __name__)

# Serve the main trivia page
@routes_bp.route("/")
def serve_frontend():
    return render_template("index.html")

# Serve the database management page (only for admins)
@routes_bp.route("/database")
def manage_database():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    return render_template("database.html")

# Serve the new_question page (only for logged_in users)
@routes_bp.route("/new_question")
def new_question():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    return render_template("new_question.html")

# Fetch all the users (for the user management page)
@routes_bp.route("/get-users", methods=["GET"])
def get_users():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    
    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403

    # Assuming you have a function to fetch all users
    users = get_all_users()
    return jsonify(users)

# Check the login status
@routes_bp.route("/login-status", methods=["GET"])
def check_login():
    """Check if the user is logged in and return their status.
    Returns:
        - logged_in (bool): True if the user is logged in, False otherwise.
        - username (str): The username of the logged-in user.
        - role (str): The role of the logged-in user (admin, user, etc.)."""
    if session.get("logged_in"):
        return jsonify({"logged_in": True, "username": session.get("username"), "role": session.get("role")})
    else:
        return jsonify({"logged_in": False})    

# Register all routes when initializing Flask
def init_routes(app):
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp)  # Register authentication routes
