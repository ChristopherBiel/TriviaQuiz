import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.user_service import create_user, update_user, get_user


def ensure_admin(username: str, email: str, password: str) -> bool:
    """Create or update an admin user with verified/approved flags."""
    existing = get_user(username)
    if existing:
        updated = update_user(
            username,
            {"role": "admin", "is_verified": True, "is_approved": True, "password": password},
            acting_role="admin",
            acting_username=username,
        )
        return bool(updated)

    user = create_user(
        {
            "username": username,
            "email": email,
            "password": password,
            "role": "admin",
            "is_verified": True,
            "is_approved": True,
        },
        acting_role="admin",
    )
    return user is not None


def main():
    parser = argparse.ArgumentParser(description="Create or update an admin user in the USERS_TABLE.")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    args = parser.parse_args()

    ok = ensure_admin(args.username, args.email, args.password)
    if not ok:
        sys.exit("Failed to create or update admin user")
    print(f"Admin user ensured for {args.username} (table={os.getenv('USERS_TABLE', 'TriviaUsersDev')})")


if __name__ == "__main__":
    main()
