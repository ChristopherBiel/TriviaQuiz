CREATE TABLE IF NOT EXISTS trivia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    media_path TEXT NULL,
    added_by TEXT NOT NULL,
    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    question_topic TEXT NULL,
    question_source TEXT NULL,
    answer_source TEXT NULL,
    expiration_date DATE NULL,
    incorrect_answer TEXT NULL,  -- Storing set of incorrect answers as a comma-separated string
    times_asked INTEGER NOT NULL DEFAULT 0,
    times_correctly_answered INTEGER NOT NULL DEFAULT 0,
    times_incorrectly_answered INTEGER NOT NULL DEFAULT 0,
    last_updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    language TEXT NULL,
    review_status BOOLEAN NOT NULL DEFAULT 0, -- 0 for not reviewed, 1 for reviewed
    tags TEXT NULL -- Storing tags as a comma-separated string
);
