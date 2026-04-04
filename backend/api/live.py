from flask import Blueprint, jsonify, request, session

from backend.services.live_service import (
    advance_question,
    create_live_session,
    finish_session,
    get_leaderboard,
    get_live_session,
    get_session_state,
    join_session,
    lock_question,
    override_answer_points,
    reveal_question,
    submit_answer,
    update_session_settings,
)

live_bp = Blueprint("live", __name__, url_prefix="/api/live")


def _require_auth():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    return None


def _require_presenter(live_session):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 403
    if session.get("username") != live_session.created_by and session.get("role") != "admin":
        return jsonify({"error": "Only the presenter can do this"}), 403
    return None


# ---------------------------------------------------------------------------
# Session management (presenter)
# ---------------------------------------------------------------------------

@live_bp.route("/", methods=["POST"])
def create_session_endpoint():
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id is required"}), 400

    show_q = data.get("show_questions_on_devices", False)
    result = create_live_session(event_id, session["username"], show_questions_on_devices=show_q)
    if not result:
        return jsonify({"error": "Failed to create session"}), 500

    return jsonify(result.model_dump(mode="json")), 201


@live_bp.route("/<session_id>/settings", methods=["PUT"])
def update_settings_endpoint(session_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    result = update_session_settings(session_id, session["username"], data)
    if not result:
        return jsonify({"error": "Session not found or not permitted"}), 404
    return jsonify(result.model_dump(mode="json")), 200


@live_bp.route("/<session_id>/advance", methods=["POST"])
def advance_endpoint(session_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    live_session = get_live_session(session_id)
    if not live_session:
        return jsonify({"error": "Session not found"}), 404

    presenter_error = _require_presenter(live_session)
    if presenter_error:
        return presenter_error

    result = advance_question(session_id, session["username"])
    if not result:
        return jsonify({"error": "Cannot advance (no more questions or session finished)"}), 400
    return jsonify(result.model_dump(mode="json")), 200


@live_bp.route("/<session_id>/lock", methods=["POST"])
def lock_endpoint(session_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    live_session = get_live_session(session_id)
    if not live_session:
        return jsonify({"error": "Session not found"}), 404

    presenter_error = _require_presenter(live_session)
    if presenter_error:
        return presenter_error

    data = request.get_json(silent=True) or {}
    question_index = data.get("question_index", live_session.current_question_index)

    result = lock_question(session_id, question_index, session["username"])
    if not result:
        return jsonify({"error": "Failed to lock question"}), 400
    return jsonify(result.model_dump(mode="json")), 200


@live_bp.route("/<session_id>/reveal", methods=["POST"])
def reveal_endpoint(session_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    live_session = get_live_session(session_id)
    if not live_session:
        return jsonify({"error": "Session not found"}), 404

    presenter_error = _require_presenter(live_session)
    if presenter_error:
        return presenter_error

    data = request.get_json(silent=True) or {}
    question_index = data.get("question_index", live_session.current_question_index)

    result = reveal_question(session_id, question_index, session["username"])
    if not result:
        return jsonify({"error": "Failed to reveal question"}), 400
    return jsonify(result), 200


@live_bp.route("/<session_id>/answer/<answer_id>/points", methods=["PATCH"])
def override_points_endpoint(session_id, answer_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    live_session = get_live_session(session_id)
    if not live_session:
        return jsonify({"error": "Session not found"}), 404

    presenter_error = _require_presenter(live_session)
    if presenter_error:
        return presenter_error

    data = request.get_json(silent=True) or {}
    points = data.get("points")
    if points is None:
        return jsonify({"error": "points is required"}), 400

    try:
        points = float(points)
    except (TypeError, ValueError):
        return jsonify({"error": "points must be a number"}), 400

    result = override_answer_points(session_id, answer_id, points, session["username"])
    if not result:
        return jsonify({"error": "Answer not found or not permitted"}), 404
    return jsonify(result.model_dump(mode="json")), 200


@live_bp.route("/<session_id>/finish", methods=["POST"])
def finish_endpoint(session_id):
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    live_session = get_live_session(session_id)
    if not live_session:
        return jsonify({"error": "Session not found"}), 404

    presenter_error = _require_presenter(live_session)
    if presenter_error:
        return presenter_error

    result = finish_session(session_id, session["username"])
    if not result:
        return jsonify({"error": "Failed to finish session"}), 400
    return jsonify(result.model_dump(mode="json")), 200


# ---------------------------------------------------------------------------
# Participant endpoints
# ---------------------------------------------------------------------------

@live_bp.route("/me", methods=["GET"])
def me_endpoint():
    """Return the current participant identity from the Flask session cookie.
    Allows the client to resume after a page refresh without rejoining."""
    pid = session.get("live_participant_id")
    sid = session.get("live_session_id")
    if not pid or not sid:
        return jsonify({"active": False}), 200
    return jsonify({"active": True, "participant_id": pid, "session_id": sid}), 200


@live_bp.route("/join", methods=["POST"])
def join_endpoint():
    data = request.get_json(silent=True) or {}
    join_code = data.get("join_code", "").strip()
    display_name = data.get("display_name", "").strip()

    if not join_code or not display_name:
        return jsonify({"error": "join_code and display_name are required"}), 400

    user_id = session.get("user_id") if session.get("logged_in") else None
    participant = join_session(join_code, display_name, user_id=user_id)
    if not participant:
        return jsonify({"error": "Invalid code or session not available"}), 404

    # Store participant identity in Flask session
    session["live_participant_id"] = participant.participant_id
    session["live_session_id"] = participant.session_id

    return jsonify(participant.model_dump(mode="json")), 201


@live_bp.route("/<session_id>/answer", methods=["POST"])
def answer_endpoint(session_id):
    participant_id = session.get("live_participant_id")
    if not participant_id or session.get("live_session_id") != session_id:
        return jsonify({"error": "Not a participant in this session"}), 403

    data = request.get_json(silent=True) or {}
    question_index = data.get("question_index")
    answer_text = data.get("answer_text", "").strip()

    if question_index is None:
        return jsonify({"error": "question_index is required"}), 400

    result = submit_answer(session_id, participant_id, question_index, answer_text)
    if not result:
        return jsonify({"error": "Cannot submit answer (locked, wrong question, or session inactive)"}), 400
    return jsonify(result.model_dump(mode="json")), 200


# ---------------------------------------------------------------------------
# Shared endpoints
# ---------------------------------------------------------------------------

@live_bp.route("/<session_id>/state", methods=["GET"])
def state_endpoint(session_id):
    live_session = get_live_session(session_id)
    if not live_session:
        return jsonify({"error": "Session not found"}), 404

    participant_id = session.get("live_participant_id")
    is_presenter = (
        session.get("logged_in")
        and (session.get("username") == live_session.created_by or session.get("role") == "admin")
    )

    # If not presenter and not participant, only allow basic info
    if not is_presenter and session.get("live_session_id") != session_id:
        participant_id = None

    state = get_session_state(
        session_id,
        participant_id=participant_id if not is_presenter else None,
        is_presenter=is_presenter,
    )
    if not state:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(state), 200
