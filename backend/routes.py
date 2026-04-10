from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from backend.auth import auth_bp, get_all_users  # Import authentication blueprint
from backend.services.event_service import get_event

routes_bp = Blueprint("routes", __name__)


def _resolve_event_id(event_id_or_slug: str) -> str | None:
    """Resolve a slug or UUID to the canonical event_id. Returns None if not found."""
    event = get_event(event_id_or_slug)
    return event.event_id if event else None

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

# Serve the manage own questions page (for logged-in users)
@routes_bp.route("/my_questions")
def my_questions():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    return render_template("my_questions.html")

# Serve the approve questions page (only for admins)
@routes_bp.route("/approve_question")
def approve_question():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    return render_template("approve_questions.html")

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

# Serve the manage events page (only for admins)
@routes_bp.route("/manage_events")
def manage_events():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    return render_template("manage_events.html")

# Serve the generate questions page (only for admins)
@routes_bp.route("/generate_questions")
def generate_questions():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    if not session.get("is_admin"):
        return jsonify({"error": "Forbidden: Admin privileges required"}), 403
    return render_template("generate_questions.html")

# Serve the events list page (public)
@routes_bp.route("/events")
def events_page():
    return render_template("events.html")

# Serve the event detail page (public)
@routes_bp.route("/events/<event_id>")
def event_detail_page(event_id):
    event = get_event(event_id)
    if not event:
        return "Event not found", 404
    if event_id != event.slug and event.slug:
        return redirect(url_for("routes.event_detail_page", event_id=event.slug), code=301)
    return render_template("event_detail.html", event_id=event.event_id)

# Serve the replay page (public)
@routes_bp.route("/events/<event_id>/replay")
def replay_event_page(event_id):
    event = get_event(event_id)
    if not event:
        return "Event not found", 404
    if event_id != event.slug and event.slug:
        return redirect(url_for("routes.replay_event_page", event_id=event.slug), code=301)
    return render_template("replay_event.html", event_id=event.event_id)

# Serve the replay detail page (login required — access checked by API)
@routes_bp.route("/events/<event_id>/replay/<replay_id>")
def replay_detail_page(event_id, replay_id):
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    event = get_event(event_id)
    if not event:
        return "Event not found", 404
    if event_id != event.slug and event.slug:
        return redirect(url_for("routes.replay_detail_page", event_id=event.slug, replay_id=replay_id), code=301)
    return render_template("replay_detail.html", event_id=event.event_id, replay_id=replay_id)

# Serve the add questions to event page (login required)
@routes_bp.route("/events/<event_id>/add-questions")
def event_add_questions_page(event_id):
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    event = get_event(event_id)
    if not event:
        return "Event not found", 404
    if event_id != event.slug and event.slug:
        return redirect(url_for("routes.event_add_questions_page", event_id=event.slug), code=301)
    return render_template("event_add_questions.html", event_id=event.event_id)

# Serve the presenter view (login required)
@routes_bp.route("/events/<event_id>/present")
def present_event_page(event_id):
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    event = get_event(event_id)
    if not event:
        return "Event not found", 404
    if event_id != event.slug and event.slug:
        return redirect(url_for("routes.present_event_page", event_id=event.slug), code=301)
    return render_template("present.html", event_id=event.event_id)

# Serve the live play join page (public)
@routes_bp.route("/live")
def live_join_page():
    return render_template("live_play.html", session_id=None)

# Serve the live play page for an active session
@routes_bp.route("/live/<session_id>")
def live_play_page(session_id):
    return render_template("live_play.html", session_id=session_id)

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

@routes_bp.route("/impressum")
def impressum():
    return render_template("impressum.html")


@routes_bp.route("/datenschutz")
def datenschutz():
    return render_template("datenschutz.html")


# Register all routes when initializing Flask
def init_routes(app):
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp)  # Register authentication routes
