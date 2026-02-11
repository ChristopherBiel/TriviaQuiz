"""
Event replay API (roadmap).

This module intentionally defines stubs only and is not yet registered
in backend.api.__init__.py. Wire it in once event replay is implemented.
"""

from flask import Blueprint, jsonify

events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.route("/", methods=["GET"])
def list_events():
    """Placeholder for listing available events."""
    return jsonify({"error": "Not implemented"}), 501
