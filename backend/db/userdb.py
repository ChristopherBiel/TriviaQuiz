import boto3
import os
import datetime

# Initialize AWS Clients
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table("TriviaUsers")

def add_user_to_db(username, email, password_hash, referral_code):
    """Adds a new user to the DynamoDB Users table."""
    
    item = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "is_verified": False,
        "is_approved": False,
        "role": "user",
        "signup_date": str(datetime.utcnow().isoformat()),
        "verification_code": None,  # This can be set later
        "verification_expiry": None,  # This can be set later
        "approval_date": None,  # This can be set later
        "last_login_date": None,
        "last_login_ip": None,
        "referral_code_used": referral_code,
    }
    
    try:
        users_table.put_item(Item=item)
        return {"status": "success", "message": "User added successfully"}
    except Exception as e:
        print("Error adding user:", str(e))
        return {"status": "error", "message": str(e)}
    
def get_user_by_username_db(username):
    """Fetches a user by their username from the DynamoDB Users table."""
    
    try:
        response = users_table.get_item(Key={"username": username})
        return response.get("Item")
    except Exception as e:
        print("Error fetching user:", str(e))
        return None

def get_all_users_db(filters=None):
    """Fetches all users from the DynamoDB Users table with optional filters."""
    
    try:
        response = users_table.scan()
        items = response.get("Items", [])
        
        if filters:
            for key, value in filters.items():
                items = [user for user in items if user.get(key) == value]
        
        return items
    except Exception as e:
        print("Error fetching users:", str(e))
        return []
    
def update_user_in_db(username, updates):
    """Updates user information in the DynamoDB Users table."""
    
    update_expression = "SET "
    expression_attribute_values = {}
    
    for key, value in updates.items():
        update_expression += f"{key} = :{key}, "
        expression_attribute_values[f":{key}"] = value
    
    update_expression = update_expression.rstrip(", ")
    
    try:
        users_table.update_item(
            Key={"username": username},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        return {"status": "success", "message": "User updated successfully"}
    except Exception as e:
        print("Error updating user:", str(e))
        return {"status": "error", "message": str(e)}

def delete_user_from_db(username):
    """Deletes a user from the DynamoDB Users table."""
    
    try:
        users_table.delete_item(Key={"username": username})
        return {"status": "success", "message": "User deleted successfully"}
    except Exception as e:
        print("Error deleting user:", str(e))
        return {"status": "error", "message": str(e)}
