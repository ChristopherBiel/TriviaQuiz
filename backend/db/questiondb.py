import boto3
import uuid
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "TriviaQuestions")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


def add_question_to_db(
    question,
    answer,
    added_by,
    question_topic=None,
    question_source=None,
    answer_source=None,
    media_file=None,
    language=None,
    incorrect_answers=None,
    tags=None,
    review_status=None
):
    question_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    item = {
        "id": question_id,
        "question": question.strip(),
        "answer": answer.strip(),
        "added_by": added_by.strip(),
        "created_at": timestamp,
        "review_status": review_status or "pending"
    }

    # Optional fields
    if question_topic: item["question_topic"] = question_topic.strip()
    if question_source: item["question_source"] = question_source.strip()
    if answer_source: item["answer_source"] = answer_source.strip()
    if language: item["language"] = language.strip()
    if incorrect_answers: item["incorrect_answers"] = [ans.strip() for ans in incorrect_answers]
    if tags: item["tags"] = [tag.strip() for tag in tags]
    if media_file:
        item["media_url"] = upload_file_to_s3(media_file)

    table.put_item(Item=item)
    return item


def get_question_by_id_db(question_id):
    response = table.get_item(Key={"id": question_id})
    return response.get("Item")


def get_all_questions_db(filters=None):
    # Full scan for now; optionally apply filters later
    response = table.scan()
    return response.get("Items", [])


def update_question_in_db(question_id, updates):
    # Only allow updating defined fields
    update_expr = []
    expr_attr_vals = {}
    for key, val in updates.items():
        update_expr.append(f"{key} = :{key}")
        expr_attr_vals[f":{key}"] = val

    if not update_expr:
        return None

    update_expression = "SET " + ", ".join(update_expr)

    response = table.update_item(
        Key={"id": question_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expr_attr_vals,
        ReturnValues="ALL_NEW"
    )
    return response.get("Attributes")


def delete_question_from_db(question_id):
    try:
        table.delete_item(Key={"id": question_id})
        return True
    except Exception:
        return False


def upload_file_to_s3(file):
    # Add your actual upload logic here (placeholder for now)
    return f"https://{os.getenv('AWS_S3_BUCKET')}.s3.{AWS_REGION}.amazonaws.com/{file.filename}"
