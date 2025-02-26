from flask import Flask, jsonify
from flask_cors import CORS  # Import Flask-CORS
import sqlite3

app = Flask(__name__)
CORS(app, origins=["http://localhost:8000"])

def get_random_question():
    conn = sqlite3.connect("trivia.db")
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer, media_path FROM trivia ORDER BY RANDOM() LIMIT 1")
    question = cursor.fetchone()
    conn.close()
    
    return {"question": question[0], "answer": question[1], "media": question[2]}

@app.route("/random-question", methods=["GET"])
def random_question():
    return jsonify(get_random_question())

if __name__ == "__main__":
    app.run(port=5600)
