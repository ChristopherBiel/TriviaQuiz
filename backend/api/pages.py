from flask import Blueprint, render_template

pages_bp = Blueprint("pages_api", __name__)


@pages_bp.route("/question/<question_id>", methods=["GET"])
def question_detail(question_id):
    return render_template("question_detail.html", question_id=question_id)

# HTML view route without colliding with the JSON API
@pages_bp.route("/questions/<question_id>/view", methods=["GET"])
def question_detail_view(question_id):
    return render_template("question_detail.html", question_id=question_id)
