from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from backend.db import get_random_question, get_all_questions, add_question, delete_question
from backend.auth import auth_bp  # Import authentication blueprint

routes_bp = Blueprint("routes", __name__)

# Serve the main trivia page
@routes_bp.route("/")
def serve_frontend():
    return render_template("index.html")

# Serve the database management page (only for logged-in users)
@routes_bp.route("/database")
def manage_database():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    return render_template("database.html")

# Fetch a random question for the trivia game
@routes_bp.route("/random-question", methods=["GET"])
def random_question():
    question = get_random_question()
    if not question:
        return jsonify({"error": "No questions found"}), 404
    return jsonify(question)

# Fetch all questions (for the database page)
@routes_bp.route("/get-questions", methods=["GET"])
def get_questions():
    questions = get_all_questions()
    return jsonify(questions)

# Add a new trivia question
@routes_bp.route("/add-question", methods=["POST"])
def add_question_route():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    question = request.form.get("question")
    answer = request.form.get("answer")
    added_by = session.get("username", "Admin")  # Default to 'Admin' if no session
    question_topic = request.form.get("question_topic")
    question_source = request.form.get("question_source", "Unknown")
    answer_source = request.form.get("answer_source", "Unknown")
    language = request.form.get("language")
    incorrect_answers = request.form.get("incorrect_answers")
    tags = request.form.get("tags")
    
    media_file = request.files.get("media")

    print(f"DEBUG: Received file: {media_file}")

    # Convert incorrect_answers and tags to lists if they exist
    if incorrect_answers:
        incorrect_answers = incorrect_answers.split(",")  # Convert CSV to list
    if tags:
        tags = tags.split(",")

    question_id = add_question(
        question, answer, added_by, question_topic, question_source, answer_source,
        media_file, language, incorrect_answers, tags
    )
    return jsonify({"success": True, "question_id": question_id})

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


# Register all routes when initializing Flask
def init_routes(app):
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp)  # Register authentication routes
