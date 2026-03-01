from flask import Blueprint, request, jsonify, session, render_template
from backend.services.question_service import (
    get_question_by_id,
    get_all_questions,
    get_question_metadata,
    count_questions,
    create_question,
    update_question,
    delete_question,
    get_random_question_filtered
)
from backend.models.question import QuestionModel
from backend.storage import get_media_store

questions_bp = Blueprint("questions", __name__, url_prefix="/questions")


def _serialize_question(question: QuestionModel) -> dict:
    data = question.model_dump(mode="json")
    # Provide both id and question_id for compatibility with legacy clients.
    if "id" not in data:
        qid = getattr(question, "question_id", None)
        if qid:
            data["id"] = qid
    media_path = getattr(question, "media_path", None) or data.get("media_path") or data.get("media_path")
    if media_path:
        resolved = get_media_store().get_url(media_path)
        if resolved:
            data["media_path"] = resolved
    return data


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes", "y"}

def _normalize_string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, list):
        return None
    cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return cleaned

def _normalize_filters(raw_filters: dict):
    filters = {k: v for k, v in raw_filters.items() if k not in {"limit", "offset"}}

    if "tags" in filters:
        tags = _normalize_string_list(filters.get("tags"))
        if tags is None:
            return None, "tags must be a comma-separated string or list of strings"
        filters["tags"] = tags
    if "language" in filters and isinstance(filters["language"], str):
        filters["language"] = filters["language"].lower()
    if "review_status" in filters:
        filters["review_status"] = _parse_bool(filters["review_status"])

    return filters, None

def _validate_question_payload(data: dict | None, partial: bool = False):
    if data is None:
        return None, "Missing request body"

    allowed_fields = {
        "question",
        "answer",
        "added_by",
        "question_topic",
        "question_source",
        "answer_source",
        "incorrect_answers",
        "language",
        "tags",
        "review_status",
        "media_path",
    }
    required_fields = {"question", "answer", "added_by"} if not partial else set()
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return None, f"Missing required fields: {', '.join(missing)}"

    sanitized = {}
    for key, value in data.items():
        if key not in allowed_fields:
            continue
        if key in {"question", "answer", "added_by", "question_topic", "question_source", "answer_source", "language", "media_path"}:
            if value is not None and not isinstance(value, str):
                return None, f"{key} must be a string"
            sanitized[key] = value.strip() if isinstance(value, str) else value
        elif key in {"incorrect_answers", "tags"}:
            normalized_list = _normalize_string_list(value)
            if normalized_list is None:
                return None, f"{key} must be a list of strings or comma-separated string"
            sanitized[key] = normalized_list
        elif key == "review_status":
            sanitized[key] = _parse_bool(value)

    if partial and not sanitized:
        return None, "No valid fields provided for update"

    return sanitized, None

def _require_role(role: str | None = None):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    if role and session.get("role") != role:
        return jsonify({"error": "Forbidden"}), 403
    return None

@questions_bp.route("/", methods=["GET"])
def list_questions():
    """List all questions, optionally filtered by query params."""
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400

    if limit < 1 or offset < 0:
        return jsonify({"error": "limit must be >= 1 and offset >= 0"}), 400

    page_token = request.args.get("page_token")
    filters, error = _normalize_filters(request.args)
    if error:
        return jsonify({"error": error}), 400

    questions, next_token = get_all_questions(filters, limit=limit, offset=offset, page_token=page_token, include_token=True)
    total = count_questions(filters)

    payload = {
        "items": [_serialize_question(question) for question in questions],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "count": len(questions),
            "total": total,
            "next_page_token": next_token
        }
    }
    return jsonify(payload), 200


@questions_bp.route("/<question_id>", methods=["GET"])
def get_question(question_id):
    """Get a specific question by ID."""
    question = get_question_by_id(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    # Serve HTML when HTML is preferred over JSON
    accepts = request.accept_mimetypes
    if accepts['text/html'] > accepts['application/json']:
        return render_template("question_detail.html", question_id=question_id)

    return jsonify(_serialize_question(question)), 200


@questions_bp.route("/", methods=["POST"])
def create_new_question():
    """Create a new question. Accepts JSON or multipart/form-data (for media upload)."""
    auth_error = _require_role()
    if auth_error:
        return auth_error

    media_file = None
    if request.files or request.form:
        media_file = request.files.get("media")
        data = request.form.to_dict()
    else:
        data = request.get_json(silent=True)

    # Auto-fill added_by from the logged-in session if the client didn't send it
    if isinstance(data, dict) and not data.get("added_by"):
        data["added_by"] = session.get("username", "")

    payload, error = _validate_question_payload(data, partial=False)
    if error:
        return jsonify({"error": error}), 400

    if media_file:
        payload["media_file"] = media_file

    new_question = create_question(payload)
    if not new_question:
        return jsonify({"error": "Failed to create question"}), 500
    return jsonify(_serialize_question(new_question)), 201


@questions_bp.route("/<question_id>", methods=["PUT"])
def update_existing_question(question_id):
    """Update an existing question."""
    auth_error = _require_role()
    if auth_error:
        return auth_error

    media_file = None
    if request.files:
        media_file = request.files.get("media")
        raw = request.form.to_dict()
        if raw.get("remove_media"):
            raw["media_path"] = None
        payload, error = _validate_question_payload(raw, partial=True)
        if error:
            return jsonify({"error": error}), 400
        if media_file:
            payload["media_file"] = media_file
    else:
        updates = request.get_json(silent=True)
        payload, error = _validate_question_payload(updates, partial=True)
        if error:
            return jsonify({"error": error}), 400

    try:
        updated_question = update_question(question_id, payload, session.get("username"), session.get("role"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if updated_question:
        return jsonify(_serialize_question(updated_question)), 200
    return jsonify({"error": "Question not found or not permitted"}), 404


@questions_bp.route("/<question_id>", methods=["DELETE"])
def delete_existing_question(question_id):
    """Delete a question."""
    auth_error = _require_role(role="admin")
    if auth_error:
        return auth_error

    success = delete_question(question_id)
    if success:
        return '', 204
    return jsonify({"error": "Question not found"}), 404

@questions_bp.route("/random", methods=["POST"])
def random_question():
    payload = request.get_json(silent=True) or {}
    seen_ids = payload.get("seen", [])
    filters, error = _normalize_filters(payload.get("filters", {}))
    if error:
        return jsonify({"error": error}), 400
    question = get_random_question_filtered(seen_ids, filters)

    if not question:
        return jsonify({"error": "No more unseen questions available."}), 404

    return jsonify(_serialize_question(question))


@questions_bp.route("/metadata", methods=["GET"])
def question_metadata():
    metadata = get_question_metadata()
    return jsonify(metadata), 200
