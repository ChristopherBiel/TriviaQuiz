from backend.db.userdb import (
    get_user_by_username_db,
    get_all_users_db,
    add_user_to_db,
    update_user_in_db,
    delete_user_from_db
)
from backend.utils.input_validation import is_email_valid, is_username_valid, is_password_valid, is_referral_code_valid
from backend.utils.password_utils import hash_password, verify_password


def get_user_by_username(username):
    """Fetch a user by username."""
    return get_user_by_username_db(username)

def get_all_users(filters=None):
    """Fetch all users, optionally filtered by provided criteria."""
    return get_all_users_db(filters)

def get_user_by_email(email):
    """Fetch a user by email, using the get_all_users function."""
    users = get_all_users({"email": email})
    if users:
        return users[0]  # Return the first user found with the given email
    return None

def create_user(data):
    """Create a new user."""
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    referral_code = data.get("referral_code")

    if not all([username, email, password]):
        raise ValueError("Missing required fields: username, email, password")
    if referral_code is None:
        referral_code = ""

    # Check if input formats are valid
    if not is_username_valid(username):
        raise ValueError("Invalid username format")
    if not is_email_valid(email):
        raise ValueError("Invalid email format")
    if not is_password_valid(password):
        raise ValueError("Invalid password format")
    if not is_referral_code_valid(referral_code):
        raise ValueError("Invalid referral code format")
    
    # Check if the user or email already exists
    existing_user = get_user_by_username(username)
    if existing_user:
        raise ValueError("Username already exists")
    existing_email = get_user_by_email(email)
    if existing_email:
        raise ValueError("Email already exists")
    
    # Add the user to the database
    return add_user_to_db(
        username=username,
        email=email,
        password_hash=hash_password(password),
        referral_code=referral_code
    )

def update_user(username, updates):
    """Update an existing user."""
    # Check if the user exists
    user = get_user_by_username(username)
    if not user:
        raise ValueError("User not found")
    # Validate the updates
    if not isinstance(updates, dict):
        raise ValueError("Updates must be a dictionary")
    allowed_updates = {"password", "role", "is_verified", "is_approved"}
    if "password" in updates and not is_password_valid(updates["password"]):
        raise ValueError("Invalid password format")
    
    if "password" in updates:
        # Hash the new password if it is being updated
        updates["password_hash"] = hash_password(updates.pop("password"))
        updates.pop("password", None)  # Remove the plain password from updates
    
    return update_user_in_db(username, updates)