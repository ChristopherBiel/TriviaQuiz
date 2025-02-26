import sqlite3

# Connect to database
conn = sqlite3.connect("trivia.db")
cursor = conn.cursor()

# List of trivia questions to add
questions = [
    ("Which artist painted the Mona Lisa?", "Leonardo da Vinci", None, "No Event"),
    ("What is the capital of France?", "Paris", None , "No Event"),
    ("Name three of the six countries bordering Libya.", "Algeria, Tunisia, Niger, Chad, Sudan, Egypt", None, "Pubquiz Towers 04.02.25")
]

# Insert data
cursor.executemany("INSERT INTO trivia (question, answer, media_path, event) VALUES (?, ?, ?, ?)", questions)
conn.commit()
conn.close()

print("Database populated successfully!")
