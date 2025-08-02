from backend.db.dynamodb import (
    get_question_by_id_db,
    get_all_questions_db,
    add_question_to_db,
    update_question_in_db,
    delete_question_from_db
)

def get_question_by_id(question_id):
    return get_question_by_id_db(question_id)

def get_all_questions(filters=None):
    return get_all_questions_db(filters)

def create_question(data):
    # Required fields
    question = data.get("question")
    answer = data.get("answer")
    added_by = data.get("added_by")

    if not all([question, answer, added_by]):
        raise ValueError("Missing required fields")

    return add_question_to_db(
        question=question,
        answer=answer,
        added_by=added_by,
        question_topic=data.get("question_topic"),
        question_source=data.get("question_source"),
        answer_source=data.get("answer_source"),
        media_file=data.get("media_file"),
        language=data.get("language"),
        incorrect_answers=data.get("incorrect_answers"),
        tags=data.get("tags"),
        review_status=data.get("review_status")
    )

def update_question(question_id, updates):
    return update_question_in_db(question_id, updates)

def delete_question(question_id):
    return delete_question_from_db(question_id)
