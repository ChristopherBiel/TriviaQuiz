import boto3
import os
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from backend.models.question import QuestionModel

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "TriviaQuestions")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


def add_question_to_db(question: QuestionModel) -> bool:
    """Adds a new question to DynamoDB."""
    item = question.model_dump(mode="json")
    # Store the canonical ID both under question_id and id for backwards compatibility.
    item["id"] = question.question_id
    table.put_item(Item=item)
    return True

def get_question_by_id_db(question_id) -> Optional[QuestionModel]:
    """Fetch a question by ID from the database."""
    if not question_id:
        print("DEBUG: No question ID provided.")
        return None
    response = table.get_item(Key={"id": question_id})
    if "Item" not in response:
        print(f"DEBUG: Question with ID {question_id} not found.")
        return None
    return QuestionModel(**response["Item"])

def get_all_questions_db(filters=None, limit: int = 50, last_key: Optional[Dict[str, Any]] = None) -> Tuple[List[QuestionModel], Optional[Dict[str, Any]]]:
    """
    Scan with optional filters and pagination.
    Returns list of questions and a pagination token (LastEvaluatedKey).
    """
    scan_kwargs: Dict[str, Any] = {"Limit": limit}
    if last_key:
        scan_kwargs["ExclusiveStartKey"] = last_key

    response = table.scan(**scan_kwargs)
    items = response.get("Items", [])

    if filters:
        for key, value in filters.items():
            if key == "tags" and isinstance(value, list):
                if value:
                    items = [item for item in items if any(tag in item.get("tags", []) for tag in value)]
            else:
                items = [item for item in items if item.get(key) == value]

    questions = [QuestionModel(**item) for item in items]
    return questions, response.get("LastEvaluatedKey")

def update_question_in_db(question_id: str, update: dict) -> QuestionModel | None:
    # Fetch the current item to get its update_history
    current = table.get_item(Key={"id": question_id}).get("Item")
    if not current:
        return None

    # Prepare update_history entry, including user if provided
    update_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "changes": update
    }
    # If 'updated_by' is in the update dict, store it in the history entry and remove it from the update dict
    if "updated_by" in update:
        update_entry["updated_by"] = update["updated_by"]
        del update["updated_by"]
    update_history = current.get("update_history", [])
    update_history.append(update_entry)

    # Only allow updating defined fields
    update_expr = []
    expr_attr_vals = {}
    for key, val in update.items():
        update_expr.append(f"{key} = :{key}")
        expr_attr_vals[f":{key}"] = val

    # Always update update_history
    update_expr.append("update_history = :update_history")
    expr_attr_vals[":update_history"] = update_history
    # Always update last_updated_at
    update_expr.append("last_updated_at = :last_updated_at")
    expr_attr_vals[":last_updated_at"] = datetime.utcnow().isoformat()

    if not update_expr:
        return None

    update_expression = "SET " + ", ".join(update_expr)

    response = table.update_item(
        Key={"id": question_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expr_attr_vals,
        ReturnValues="ALL_NEW"
    )
    attrs = response.get("Attributes")
    if attrs:
        return QuestionModel(**attrs)
    return None

def delete_question_from_db(question_id):
    try:
        table.delete_item(Key={"id": question_id})
        return True
    except Exception:
        return False
