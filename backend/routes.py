from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from backend.db import get_db

routes_bp = Blueprint("routes", __name__)

@routes_bp.route("/")
def serve_frontend():
    return render_template("index.html")

@routes_bp.route("/random-question", methods=["GET"])
def random_question():
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM trivia ORDER BY RANDOM() LIMIT 1")
    question = cursor.fetchone()
    return jsonify(dict(question)) if question else jsonify({"error": "No questions found."})

@routes_bp.route("/database")
def manage_database():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    return render_template("database.html")

def init_routes(app):
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp)
