from flask import Flask, g, jsonify, render_template, request, redirect, url_for, session
import sqlite3
import os
import time
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from backend/logindata.env
env_path = os.path.join(os.path.dirname(__file__), "backend", "logindata.env")
load_dotenv(env_path)

# Retrieve credentials from .env
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
print(ADMIN_USERNAME, ADMIN_PASSWORD, SECRET_KEY)
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "mp3", "mp4"}
app.secret_key = SECRET_KEY

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect("trivia.db")
        g.db.row_factory = sqlite3.Row  # Enables column access by name
    return g.db

@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("manage_database"))
        return "Invalid credentials", 403  # Show error if wrong login

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Fetch a random question
@app.route("/random-question", methods=["GET"])
def random_question():
    cursor = get_db().cursor()
    cursor.execute("SELECT id, question, answer, media_path FROM trivia ORDER BY RANDOM() LIMIT 1")
    question = cursor.fetchone()
    if question is None:
        return jsonify({"error": "No questions found."})
    return jsonify({
        "id": question["id"],
        "question": question["question"],
        "answer": question["answer"],
        "media": question["media_path"]
    })

# Fetch all questions for the database management page
@app.route("/get-questions", methods=["GET"])
def get_questions():
    cursor = get_db().cursor()
    cursor.execute("SELECT id, question, answer, media_path FROM trivia")
    questions = cursor.fetchall()
    return jsonify([{ "id": q["id"], "question": q["question"], "answer": q["answer"], "media": q["media_path"] } for q in questions])

# Add a new question to the database
@app.route("/add-question", methods=["POST"])
def add_question():
    question = request.form.get("question")
    answer = request.form.get("answer")
    media_path = None

    if "media" in request.files:
        file = request.files["media"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            # If the file already exists, rename it
            if os.path.exists(filepath):
                filename = f"{int(time.time())}_{filename}"  # Append timestamp
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            file.save(filepath)
            media_path = f"uploads/{filename}"

    db = get_db()
    db.execute("INSERT INTO trivia (question, answer, media_path) VALUES (?, ?, ?)", (question, answer, media_path))
    db.commit()

    return redirect(url_for("manage_database"))

# Delete a question by ID
@app.route("/delete-question/<int:id>", methods=["DELETE"])
def delete_question(id):
    cursor = get_db().cursor()
    cursor.execute("DELETE FROM trivia WHERE id = ?", (id,))
    get_db().commit()
    return jsonify({"success": True})

# Serve database management page
@app.route("/database")
def manage_database():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("database.html")

# Serve frontend
@app.route("/")
def serve_frontend():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5600)
