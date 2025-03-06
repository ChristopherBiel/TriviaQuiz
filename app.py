from flask import Flask, jsonify, render_template, request, g
import sqlite3

app = Flask(__name__)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect("trivia.db")
        g.db.row_factory = sqlite3.Row  # Enables column access by name
    return g.db

@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

# Fetch a random question
@app.route("/random-question", methods=["GET"])
def random_question():
    cursor = get_db().cursor()
    cursor.execute("SELECT id, question, answer, media_path FROM trivia ORDER BY RANDOM() LIMIT 1")
    question = cursor.fetchone()
    if question is None:
        return jsonify({"error": "No questions found in the database."})
    return jsonify({"id": question["id"], "question": question["question"], "answer": question["answer"], "media": question["media_path"]})

# Fetch all questions for the database management page
@app.route("/get-questions", methods=["GET"])
def get_questions():
    cursor = get_db().cursor()
    cursor.execute("SELECT id, question, answer FROM trivia")
    questions = cursor.fetchall()
    return jsonify([{ "id": q["id"], "question": q["question"], "answer": q["answer"] } for q in questions])

# Add a new question to the database
@app.route("/add-question", methods=["POST"])
def add_question():
    data = request.json
    cursor = get_db().cursor()
    cursor.execute("INSERT INTO trivia (question, answer, media_path) VALUES (?, ?, ?)", (data["question"], data["answer"], data.get("media", None)))
    get_db().commit()
    return jsonify({"success": True})

# Delete a question by ID
@app.route("/delete-question/<int:id>", methods=["DELETE"])
def delete_question(id):
    cursor = get_db().cursor()
    cursor.execute("DELETE FROM trivia WHERE id = ?", (id,))
    get_db().commit()
    return jsonify({"success": True})

# Serve frontend
@app.route("/")
def serve_frontend():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5600)
