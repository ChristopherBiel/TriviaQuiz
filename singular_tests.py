from backend.models.question import QuestionModel

example_question = QuestionModel(
    question="Example question?",
    answer="Example answer",
    added_by="user123",
    question_topic="General",
    language="English",
    tags=["example", "test"]
)

print(example_question.model_dump_json())
print(example_question.model_dump())