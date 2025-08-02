from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from backend.db import get_random_question, get_all_questions, add_question, delete_question, approve_question, reject_question, get_question_metadata
from backend.auth import auth_bp, edit_user, get_all_users  # Import authentication blueprint

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

# Fetch a random question for the trivia game
@routes_bp.route("/random-question", methods=["POST"])
def random_question():
    seen_ids = request.json.get("seen", [])
    filters = request.json.get("filters", {})
    question = get_random_question(seen_ids, filters)

    if not question:
        return jsonify({"error": "No more unseen questions available."}), 404

    return jsonify(question)

# Fetch all questions (for the database page)
@routes_bp.route("/get-questions", methods=["GET"])
def get_questions():
    questions = get_all_questions()
    return jsonify(questions)

# Fetch all metadata (to sort questions by language, topic, etc.)
@routes_bp.route("/question-metadata", methods=["GET"])
def question_metadata():
    metadata = get_question_metadata()
    return jsonify(metadata)

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

# Add a new trivia question
@routes_bp.route("/add-question", methods=["POST"])
def add_question_route():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    question = request.form.get("question")
    answer = request.form.get("answer")
    added_by = session.get("username", "guest")  # Default to 'Admin' if no session
    question_topic = request.form.get("question_topic")
    question_source = request.form.get("question_source", "Unknown")
    answer_source = request.form.get("answer_source", "Unknown")
    language = request.form.get("language")
    incorrect_answers = request.form.get("incorrect_answers")
    tags = request.form.get("tags")
    review_status = True if session.get("is_admin") else False      # Admin questions are automatically reviewed
    
    media_file = request.files.get("media")

    print(f"DEBUG: Received file: {media_file}")

    # Convert incorrect_answers and tags to lists if they exist
    if incorrect_answers:
        incorrect_answers = incorrect_answers.split(",")  # Convert CSV to list
    if tags:
        tags = tags.split(",")

    question_id = add_question(
        question, answer, added_by, question_topic, question_source, answer_source,
        media_file, language, incorrect_answers, tags, review_status
    )
    return jsonify({"success": True, "question_id": question_id})

# Approve a trivia question
@routes_bp.route("/approve-question/<string:id>/<string:topic>", methods=["POST"])
def approve_question_route(id, topic):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403

    success = approve_question(id, topic)
    
    if success:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Failed to approve question"}), 500
    
# Reject a trivia question
@routes_bp.route("/reject-question/<string:id>/<string:topic>", methods=["POST"])
def reject_question_route(id, topic):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403

    success = reject_question(id, topic)
    
    if success:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Failed to reject question"}), 500

# Delete a trivia question
@routes_bp.route("/delete-question/<string:id>/<string:topic>", methods=["DELETE"])
def delete_question_route(id, topic):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    success = delete_question(id, topic)
    
    if success:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Failed to delete question"}), 500

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

# Approve a user (only for admins)
@routes_bp.route("/users/<string:username>/<string:action>", methods=["POST"])
def edit_user_permissions(username, action):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403

    success = edit_user(username, action)

    if success:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Failed to approve user"}), 500

# Delete a user (only for admins)
@routes_bp.route("/users/<string:username>", methods=["DELETE"])
def delete_user(username):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403

    success = edit_user(username, "delete")
    if success:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Failed to delete user"}), 500


# Register all routes when initializing Flask
def init_routes(app):
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp)  # Register authentication routes
