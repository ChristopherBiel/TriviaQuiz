import boto3
import os
from flask import Blueprint, request, session, redirect, url_for, render_template

auth_bp = Blueprint("auth", __name__)

# Initialize AWS Systems Manager Client
ssm = boto3.client("ssm", region_name="eu-central-1")

def get_parameter(name):
    """Retrieve parameter from AWS Systems Manager Parameter Store."""
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]

# Load credentials from AWS Systems Manager
ADMIN_USERNAME = get_parameter("/TriviaQuiz/ADMIN_USERNAME")
ADMIN_PASSWORD = get_parameter("/TriviaQuiz/ADMIN_PASSWORD")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("manage_database"))
        return "Invalid credentials", 403
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
