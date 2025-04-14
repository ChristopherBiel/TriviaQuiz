import boto3
import os
import bcrypt
from datetime import datetime
from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template, flash
from markupsafe import escape
import re

auth_bp = Blueprint("auth", __name__)

# Initialize AWS Clients
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
ssm = boto3.client("ssm", region_name=AWS_REGION)
users_table = dynamodb.Table("TriviaUsers")

# Fetch referral code from AWS Systems Manager Parameter Store
REFERRAL_CODE_PARAM = "/TriviaQuiz/REFERRAL_CODE"
def get_referral_code():
    try:
        response = ssm.get_parameter(Name=REFERRAL_CODE_PARAM, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception as e:
        print("Error fetching referral code:", str(e))
        return None

# ----- CAN BE REMOVED IF NEW USER LOGGING VIA DATABASE WORKS -----
def get_parameter(name):
    """Retrieve parameter from AWS Systems Manager Parameter Store."""
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]

# Load credentials from AWS Systems Manager
ADMIN_USERNAME = get_parameter("/TriviaQuiz/ADMIN_USERNAME")
ADMIN_PASSWORD = get_parameter("/TriviaQuiz/ADMIN_PASSWORD")
# ----- END OF CAN BE REMOVED -----

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    # Accept data from HTML form and sanitize it
    username = escape(request.form.get("username", "").strip())
    email = escape(request.form.get("email", "").strip())
    password = request.form.get("password", "")
    referral_code = escape(request.form.get("referral_code", "").strip())

    if not username or not email or not password or not referral_code:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    if not re.match(r"^[\w.@+-]+$", username):
        return jsonify({"status": "error", "message": "Username contains invalid characters"}), 400

    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return jsonify({"status": "error", "message": "Invalid email format"}), 400

    stored_referral_code = get_referral_code()
    if stored_referral_code is None:
        return jsonify({"status": "error", "message": "Referral system not configured"}), 500

    if referral_code != stored_referral_code:
        return jsonify({"status": "error", "message": "Invalid referral code"}), 403

    existing_user = users_table.get_item(Key={"username": username}).get("Item")
    if existing_user:
        return jsonify({"status": "error", "message": "Username already exists"}), 400

    password_hash = hash_password(password)

    users_table.put_item(
        Item={
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "is_verified": False,
            "is_approved": False,
            "role": "user",
            "signup_date": str(datetime.utcnow().isoformat()),
            "verification_code": None,
            "verification_code_expiry": None,
            "approval_date": None,
            "last_login_date": None,
            "last_login_ip": None,
            "referral_code_used": referral_code,
        }
    )
    return jsonify({"status": "success", "message": "Signup successful, please wait for admin approval."}), 201




@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    # Try form data first
    username = request.form.get("username")
    password = request.form.get("password")

    # Fallback to JSON if form data is empty
    if not username or not password:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Missing login data"}), 400
        username = data.get("username")
        password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    user = users_table.get_item(Key={"username": username}).get("Item")
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user["is_approved"]:
        return jsonify({"error": "Admin approval required"}), 403

    # Update last login date and IP
    users_table.update_item(
        Key={"username": username},
        UpdateExpression="SET last_login_date = :date, last_login_ip = :ip",
        ExpressionAttributeValues={
            ":date": str(datetime.utcnow()),
            ":ip": request.remote_addr
        }
    )

    # Set session variables
    session["logged_in"] = True
    session["username"] = user["username"]
    session["email"] = user["email"]
    session["role"] = user["role"]
    session["is_admin"] = user["role"] == "admin"
    return redirect("/")


@auth_bp.route("/approve_user", methods=["GET"])
def approve_user():
    return render_template("approve_user.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("routes.serve_frontend"))

def get_all_users():
    """Fetch all users from DynamoDB."""
    try:
        response = users_table.scan()
        return response.get("Items", [])
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

def edit_user(user_id, action):
    """Edit user details in DynamoDB."""
    try:
        if action == "approve":
            users_table.update_item(
                Key={"username": user_id},
                UpdateExpression="SET is_approved = :val, approval_date = :date, approved_by = :admin",
                ExpressionAttributeValues={
                    ":val": True,
                    ":date": datetime.utcnow().isoformat(),
                    ":admin": session["username"]
                }
            )
        elif action == "reject":
            users_table.update_item(
                Key={"username": user_id},
                UpdateExpression="SET is_approved = :val, approval_date = :date, approved_by = :admin",
                ExpressionAttributeValues={
                    ":val": False,
                    ":date": datetime.utcnow().isoformat(),
                    ":admin": session["username"]
                }
            )
        elif action == "make_admin":
            users_table.update_item(
                Key={"username": user_id},
                UpdateExpression="SET role = :val",
                ExpressionAttributeValues={":val": "admin"}
            )
        elif action == "delete":
            users_table.delete_item(Key={"username": user_id})
        else:
            return False
        return True
    except Exception as e:
        print(f"Error editing user: {e}")
        return False