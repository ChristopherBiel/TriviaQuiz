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
    if "no_incorrect_answers" in filters:
        filters["no_incorrect_answers"] = _parse_bool(filters["no_incorrect_answers"])
    if "no_media" in filters:
        filters["no_media"] = _parse_bool(filters["no_media"])

    return filters, None

def _validate_question_payload(data: dict | None, partial: bool = False):
    if data is None:
        return None, "Missing request body"

    allowed_fields = {
        "question",
        "answer",
        "added_by",
        "question_topic",
        "event_id",
        "source_note",
        "answer_source",
        "incorrect_answers",
        "language",
        "tags",
        "review_status",
        "media_path",
        "media_text",
        "points",
    }
    required_fields = {"question", "answer", "added_by"} if not partial else set()
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return None, f"Missing required fields: {', '.join(missing)}"

    sanitized = {}
    for key, value in data.items():
        if key not in allowed_fields:
            continue
        if key in {"question", "answer", "added_by", "question_topic", "event_id", "source_note", "answer_source", "language", "media_path", "media_text"}:
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
        elif key == "points":
            try:
                points_val = int(value)
            except (TypeError, ValueError):
                return None, "points must be an integer"
            if points_val < 1 or points_val > 10:
                return None, "points must be between 1 and 10"
            sanitized[key] = points_val

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

    # Auto-add to event if event_id was provided
    if new_question.event_id:
        from backend.services.event_service import add_question_to_event
        add_question_to_event(new_question.event_id, new_question.question_id)

    return jsonify(_serialize_question(new_question)), 201


@questions_bp.route("/<question_id>", methods=["PUT"])
def update_existing_question(question_id):
    """Update an existing question."""
    auth_error = _require_role()
    if auth_error:
        return auth_error

    media_file = None
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        media_file = request.files.get("media")
        raw = request.form.to_dict()
        if raw.get("remove_media"):
            raw["media_path"] = None
        if raw.get("remove_media_text"):
            raw["media_text"] = None
        payload, error = _validate_question_payload(raw, partial=True)
        if error and not media_file:
            return jsonify({"error": error}), 400
        if payload is None:
            payload = {}
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
    """Delete a question. Creator or admin can delete."""
    auth_error = _require_role()
    if auth_error:
        return auth_error

    # Check ownership: creator or admin
    question = get_question_by_id(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    username = session.get("username")
    role = session.get("role")
    if question.added_by != username and role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    confirm = request.args.get("confirm", "").lower() in ("true", "1", "yes")
    result = delete_question(question_id, confirm=confirm)
    if result.get("linked_event_id"):
        return jsonify({
            "error": "Question is linked to an event",
            "event_id": result["linked_event_id"],
        }), 409
    if result.get("success"):
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


@questions_bp.route("/format-examples", methods=["POST"])
def format_examples():
    """Return filtered questions as copyable text. Admin only."""
    auth_error = _require_role("admin")
    if auth_error:
        return auth_error

    import random
    from backend.utils.question_generator import QuestionGenerator

    body = request.get_json(silent=True) or {}
    raw_filters = body.get("filters", {})
    limit = min(int(body.get("limit", 10)), 50)

    filters, error = _normalize_filters(raw_filters)
    if error:
        return jsonify({"error": error}), 400

    # Fetch a larger pool and randomly sample for variety
    pool_size = min(limit * 5, 200)
    pool = get_all_questions(filters, limit=pool_size, offset=0)
    if not pool:
        return jsonify({"error": "No questions match the given filters"}), 404

    questions = random.sample(pool, min(limit, len(pool)))
    examples = [_serialize_question(q) for q in questions]
    text = QuestionGenerator.format_examples_text(examples)
    return jsonify({"text": text, "count": len(examples)}), 200


@questions_bp.route("/generate", methods=["POST"])
def generate_questions():
    """Generate new questions via AI based on filtered examples. Admin only."""
    auth_error = _require_role("admin")
    if auth_error:
        return auth_error

    from backend.utils.question_generator import get_generator, GenerationError
    from backend.utils.rate_limit import question_gen_limiter

    username = session.get("username", "")
    if not question_gen_limiter.is_allowed(username):
        remaining = question_gen_limiter.remaining(username)
        return jsonify({"error": "Rate limit exceeded. Try again later.", "remaining": remaining}), 429

    generator = get_generator()
    if generator is None:
        return jsonify({"error": "AI generation is not configured. Set LLM_EVAL_ENABLED=1 and provide an API key."}), 503

    body = request.get_json(silent=True) or {}
    raw_filters = body.get("filters", {})
    count = min(int(body.get("count", 5)), 20)
    extra_instructions = body.get("extra_instructions", "")

    filters, error = _normalize_filters(raw_filters)
    if error:
        return jsonify({"error": error}), 400

    import random

    # Fetch a larger pool and randomly sample for variety
    pool = get_all_questions(filters, limit=50, offset=0)
    if len(pool) < 2:
        return jsonify({"error": "Need at least 2 example questions matching the filters"}), 400

    questions = random.sample(pool, min(10, len(pool)))
    examples = [_serialize_question(q) for q in questions]
    language = filters.get("language")
    topic = filters.get("question_topic")

    try:
        generated = generator.generate(examples, count, language=language, topic=topic, extra_instructions=extra_instructions or None)
    except GenerationError as exc:
        return jsonify({"error": str(exc)}), 502

    question_gen_limiter.record(username)
    return jsonify({
        "generated": generated,
        "example_count": len(examples),
        "remaining_generations": question_gen_limiter.remaining(username),
    }), 200


@questions_bp.route("/bulk-create", methods=["POST"])
def bulk_create_questions():
    """Create multiple questions at once. Admin only."""
    auth_error = _require_role("admin")
    if auth_error:
        return auth_error

    body = request.get_json(silent=True) or {}
    items = body.get("questions", [])
    if not isinstance(items, list) or not items:
        return jsonify({"error": "questions must be a non-empty array"}), 400

    username = session.get("username", "")
    created = []
    failed = 0

    for item in items:
        item["added_by"] = username
        item.setdefault("review_status", True)
        item.setdefault("source_note", "AI-generated")

        payload, error = _validate_question_payload(item, partial=False)
        if error:
            failed += 1
            continue

        new_question = create_question(payload)
        if new_question:
            created.append(_serialize_question(new_question))
        else:
            failed += 1

    return jsonify({"created": created, "failed": failed}), 201
