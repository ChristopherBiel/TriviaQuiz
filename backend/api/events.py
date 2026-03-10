from flask import Blueprint, jsonify, request, session

from backend.services.event_service import (
    add_question_to_event,
    create_event,
    delete_event,
    get_event,
    get_event_questions,
    list_events,
    remove_question_from_event,
    reorder_event_questions,
    update_event,
)
from backend.services.replay_service import (
    delete_replay,
    evaluate_replay,
    get_leaderboard,
    get_replay_detail,
    has_played_event,
    start_replay,
    submit_replay,
)
from backend.storage import get_media_store

events_bp = Blueprint("events", __name__, url_prefix="/api/events")


def _require_auth():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    return None


def _serialize_question(question):
    data = question.model_dump(mode="json")
    if "id" not in data:
        qid = getattr(question, "question_id", None)
        if qid:
            data["id"] = qid
    media_path = getattr(question, "media_path", None) or data.get("media_path")
    if media_path:
        resolved = get_media_store().get_url(media_path)
        if resolved:
            data["media_path"] = resolved
    return data


# ---------------------------------------------------------------------------
# Event CRUD
# ---------------------------------------------------------------------------

@events_bp.route("/", methods=["GET"])
def list_events_endpoint():
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400

    filters = {}
    if request.args.get("created_by"):
        filters["created_by"] = request.args["created_by"]

    events, total = list_events(filters=filters or None, limit=limit, offset=offset)
    return jsonify({
        "items": [e.model_dump(mode="json") for e in events],
        "pagination": {"limit": limit, "offset": offset, "count": len(events), "total": total},
    }), 200


@events_bp.route("/<event_id>", methods=["GET"])
def get_event_endpoint(event_id):
    event = get_event(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    leaderboard = get_leaderboard(event_id, limit=5)
    data = event.model_dump(mode="json")
    data["leaderboard"] = leaderboard
    return jsonify(data), 200


@events_bp.route("/", methods=["POST"])
def create_event_endpoint():
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True)
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    event = create_event(data, session["username"])
    if not event:
        return jsonify({"error": "Failed to create event"}), 500
    return jsonify(event.model_dump(mode="json")), 201


@events_bp.route("/<event_id>", methods=["PUT"])
def update_event_endpoint(event_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    updates = request.get_json(silent=True)
    if not updates:
        return jsonify({"error": "Missing request body"}), 400

    result = update_event(event_id, updates, session["username"], session.get("role", "user"))
    if not result:
        return jsonify({"error": "Event not found or not permitted"}), 404
    return jsonify(result.model_dump(mode="json")), 200


@events_bp.route("/<event_id>", methods=["DELETE"])
def delete_event_endpoint(event_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    delete_questions = request.args.get("delete_questions", "").lower() in ("true", "1", "yes")
    success = delete_event(event_id, session["username"], session.get("role", "user"), delete_questions)
    if success:
        return "", 204
    return jsonify({"error": "Event not found or not permitted"}), 404


# ---------------------------------------------------------------------------
# Event questions
# ---------------------------------------------------------------------------

@events_bp.route("/<event_id>/questions", methods=["GET"])
def get_event_questions_endpoint(event_id):
    event = get_event(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    logged_in = session.get("logged_in", False)
    user_id = session.get("user_id")
    username = session.get("username")
    role = session.get("role", "user")

    is_owner_or_admin = logged_in and (username == event.created_by or role == "admin")
    answers_visible = is_owner_or_admin or (
        logged_in and bool(user_id) and has_played_event(event_id, user_id)
    )

    questions = get_event_questions(event_id)
    serialized = []
    for q in questions:
        data = _serialize_question(q)
        if not answers_visible:
            data["answer"] = None
        serialized.append(data)

    return jsonify({"items": serialized, "answers_visible": answers_visible}), 200


@events_bp.route("/<event_id>/questions", methods=["POST"])
def add_questions_to_event_endpoint(event_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    question_ids = data.get("question_ids", [])
    if not question_ids:
        return jsonify({"error": "question_ids is required"}), 400

    added = []
    for qid in question_ids:
        if add_question_to_event(event_id, qid):
            added.append(qid)

    return jsonify({"added": added}), 200


@events_bp.route("/<event_id>/questions/<question_id>", methods=["DELETE"])
def remove_question_from_event_endpoint(event_id, question_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    success = remove_question_from_event(event_id, question_id)
    if success:
        return "", 204
    return jsonify({"error": "Not found"}), 404


@events_bp.route("/<event_id>/questions/order", methods=["PUT"])
def reorder_questions_endpoint(event_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    question_ids = data.get("question_ids", [])
    if not question_ids:
        return jsonify({"error": "question_ids is required"}), 400

    success = reorder_event_questions(event_id, question_ids)
    if not success:
        return jsonify({"error": "Invalid question_ids or event not found"}), 400
    return jsonify({"success": True}), 200


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

@events_bp.route("/<event_id>/replay", methods=["POST"])
def start_replay_endpoint(event_id):
    data = start_replay(event_id)
    if not data:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(data), 200


@events_bp.route("/<event_id>/replay/evaluate", methods=["POST"])
def evaluate_replay_endpoint(event_id):
    """Evaluate answers without saving — anyone can call this."""
    data = request.get_json(silent=True) or {}
    user_answers = data.get("answers", [])

    try:
        result = evaluate_replay(event_id, user_answers)
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Evaluation failed unexpectedly"}), 500

    if result is None:
        return jsonify({"error": "Event not found"}), 404

    return jsonify(result), 200


@events_bp.route("/<event_id>/replay/submit", methods=["POST"])
def submit_replay_endpoint(event_id):
    """Submit and save replay — requires login."""
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    user_answers = data.get("answers", [])
    display_name = data.get("display_name") or session.get("username")
    user_id = session.get("user_id")

    replay = submit_replay(event_id, user_answers, user_id=user_id, display_name=display_name)
    if not replay:
        return jsonify({"error": "Event not found"}), 404

    return jsonify(replay.model_dump(mode="json")), 201


@events_bp.route("/<event_id>/replay/<replay_id>", methods=["GET"])
def get_replay_endpoint(event_id, replay_id):
    """Return full replay details. Accessible to replay owner, event owner, or admin."""
    detail = get_replay_detail(replay_id)
    if not detail or detail["event_id"] != event_id:
        return jsonify({"error": "Replay not found"}), 404

    logged_in = session.get("logged_in", False)
    user_id = session.get("user_id")
    role = session.get("role", "user")

    # Check access: replay owner, event owner, or admin
    is_admin = role == "admin"
    is_replay_owner = logged_in and user_id and detail.get("user_id") == user_id
    if not is_admin and not is_replay_owner:
        from backend.services.event_service import get_event
        event = get_event(event_id)
        is_event_owner = logged_in and event and session.get("username") == event.created_by
        if not is_event_owner:
            return jsonify({"error": "Forbidden"}), 403

    return jsonify(detail), 200


@events_bp.route("/<event_id>/replay/<replay_id>", methods=["DELETE"])
def delete_replay_endpoint(event_id, replay_id):
    """Delete a replay record — admin only."""
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    if session.get("role") != "admin":
        return jsonify({"error": "Admin required"}), 403

    if delete_replay(replay_id, event_id):
        return "", 204
    return jsonify({"error": "Replay not found"}), 404


@events_bp.route("/<event_id>/leaderboard", methods=["GET"])
def leaderboard_endpoint(event_id):
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10
    data = get_leaderboard(event_id, limit=limit)
    return jsonify({"items": data}), 200
