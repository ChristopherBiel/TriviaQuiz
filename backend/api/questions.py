from flask import Blueprint, request, jsonify
from backend.services.question_service import (
    get_question_by_id,
    get_all_questions,
    create_question,
    update_question,
    delete_question,
    get_random_question_filtered
)

questions_bp = Blueprint("questions", __name__, url_prefix="/questions")


@questions_bp.route("/", methods=["GET"])
def list_questions():
    """List all questions, optionally filtered by query params."""
    filters = request.args.to_dict()
    questions = get_all_questions(filters)
    return jsonify(questions), 200


@questions_bp.route("/<question_id>", methods=["GET"])
def get_question(question_id):
    """Get a specific question by ID."""
    question = get_question_by_id(question_id)
    if question:
        return jsonify(question), 200
    return jsonify({"error": "Question not found"}), 404


@questions_bp.route("/", methods=["POST"])
def create_new_question():
    """Create a new question."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    new_question = create_question(data)
    return jsonify(new_question), 201


@questions_bp.route("/<question_id>", methods=["PUT"])
def update_existing_question(question_id):
    """Update an existing question."""
    updates = request.get_json()
    if not updates:
        return jsonify({"error": "Missing update data"}), 400

    updated_question = update_question(question_id, updates)
    if updated_question:
        return jsonify(updated_question), 200
    return jsonify({"error": "Question not found"}), 404


@questions_bp.route("/<question_id>", methods=["DELETE"])
def delete_existing_question(question_id):
    """Delete a question."""
    success = delete_question(question_id)
    if success:
        return '', 204
    return jsonify({"error": "Question not found"}), 404

@questions_bp.route("/random", methods=["POST"])
def random_question():
    seen_ids = request.json.get("seen", [])
    filters = request.json.get("filters", {})
    question = get_random_question_filtered(seen_ids, filters)

    if not question:
        return jsonify({"error": "No more unseen questions available."}), 404

    return jsonify(question)
