import re

def is_username_valid(username: str) -> bool:
    """
    Check if the username is valid.
    Valid usernames must be alphanumeric and can include underscores, with a length between 3 and 20 characters.
    """
    return bool(re.match(r"^[a-zA-Z0-9_]{3,20}$", username))

def is_email_valid(email: str) -> bool:
    """
    Check if the email is valid.
    Valid emails must follow the standard email format.
    """
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))

def is_password_valid(password: str) -> bool:
    """
    Check if the password is valid.
    Valid passwords must be at least 8 characters long.
    """
    return len(password) >= 8

def is_referral_code_valid(referral_code: str) -> bool:
    """
    Check if the referral code is valid.
    Valid referral codes must be exactly 6 characters long.
    """
    return bool(re.match(r"^[a-zA-Z0-9]{6}$", referral_code))
    
def is_loose_input_valid(text: str, max_len: int = 1000) -> bool:
    """
    Validates input with loose rules: basic length check and removes clearly dangerous tags.
    """
    if len(text) > max_len:
        return False
    # Basic check for script tags or control characters
    if re.search(r'<\s*script|[\x00-\x1F\x7F]', text, re.IGNORECASE):
        return False
    return True