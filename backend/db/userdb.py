import boto3
import os
from datetime import datetime
from backend.models.user import UserModel

# Initialize AWS Clients
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
USERS_TABLE = os.getenv("USERS_TABLE", "TriviaUsersDev")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USERS_TABLE)

def add_user_to_db(user: UserModel) -> bool:
    """Adds a new user to the DynamoDB Users table (partition key: user_id)."""
    item = user.model_dump(mode="json")
    item["user_id"] = user.user_id
    try:
        users_table.put_item(Item=item)
        return True
    except Exception as e:
        print("Error adding user:", str(e))
        return False
    
def get_user_by_username_db(username) -> UserModel | None:
    """Fetches a user by their username from the DynamoDB Users table."""
    try:
        response = users_table.scan(
            FilterExpression="username = :u",
            ExpressionAttributeValues={":u": username}
        )
        items = response.get("Items", [])
        if not items:
            return None
        return UserModel(**items[0])
    except Exception as e:
        print("Error fetching user:", str(e))
        return None


def get_user_by_id_db(user_id: str) -> UserModel | None:
    try:
        response = users_table.get_item(Key={"user_id": user_id})
        item = response.get("Item")
        return UserModel(**item) if item else None
    except Exception as e:
        print("Error fetching user by id:", str(e))
        return None

def get_all_users_db(filters=None):
    """Fetches all users from the DynamoDB Users table with optional filters."""
    try:
        response = users_table.scan()
        items = response.get("Items", [])
        if filters:
            for key, value in filters.items():
                items = [user for user in items if user.get(key) == value]
        return [UserModel(**item) for item in items]
    except Exception as e:
        print("Error fetching users:", str(e))
        return []
    
def update_user_in_db(user_id, updates) -> UserModel | None:
    """Updates user information in the DynamoDB Users table."""
    update_expression = []
    expression_attribute_values = {}

    for key, value in updates.items():
        update_expression.append(f"{key} = :{key}")
        expression_attribute_values[f":{key}"] = value

    if not update_expression:
        return None

    update_expression = "SET " + ", ".join(update_expression)

    try:
        resp = users_table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW",
        )
        item = resp.get("Attributes")
        return UserModel(**item) if item else None
    except Exception as e:
        print("Error updating user:", str(e))
        return None

def delete_user_from_db(user_id) -> bool:
    """Deletes a user from the DynamoDB Users table."""
    try:
        users_table.delete_item(Key={"user_id": user_id})
        return True
    except Exception as e:
        print("Error deleting user:", str(e))
        return False
