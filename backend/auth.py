from flask import Blueprint, request, session, redirect, url_for, render_template
import os
from dotenv import load_dotenv

auth_bp = Blueprint("auth", __name__)

# Load environment variables from backend/logindata.env
env_path = os.path.join(os.path.dirname(__file__), "logindata.env")
load_dotenv(env_path)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


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