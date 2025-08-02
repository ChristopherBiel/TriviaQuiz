from backend.db.userdb import (
    get_user_by_username_db,
    get_all_users_db,
    add_user_to_db,
    update_user_in_db,
    delete_user_from_db
)

def get_user_by_username(username):
    """Fetch a user by username."""
    return get_user_by_username_db(username)

def get_all_users(filters=None):
    """Fetch all users, optionally filtered by provided criteria."""
    return get_all_users_db(filters)

def create_user(data):
    """Create a new user."""
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    referral_code = data.get("referral_code")

    if not all([username, email, password]):
        raise ValueError("Missing required fields: username, email, password")
    
    # Check if the username is valid (alphanumeric and underscores only)
    if not username.isalnum() and "_" not in username:
        raise ValueError("Username must be alphanumeric or contain underscores only")
    if len(username) < 3 or len(username) > 20:
        raise ValueError("Username must be between 3 and 20 characters long")
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Invalid email format")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if referral_code and len(referral_code) != 6:
        raise ValueError("Referral code must be exactly 6 characters long")
    if not referral_code:
        referral_code = None
    

    # Check if the user or email already exists
