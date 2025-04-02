import boto3
import uuid
import os
from datetime import datetime
import random
import mimetypes

# Load AWS region from environment variable
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table("TriviaQuestions")

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "chris-trivia-media-bucket")

s3 = boto3.client("s3", region_name=AWS_REGION)

# Add a new question to DynamoDB
def add_question(question, answer, added_by, question_topic=None, question_source=None, answer_source=None,
                 media_file=None, language=None, incorrect_answers=None, tags=None):
    """Adds a new question to DynamoDB."""
    question_id = str(uuid.uuid4())  # Generate unique ID

    media_path = None
    if media_file:
        media_path = upload_file_to_s3(media_file)

    item = {
        "id": question_id,
        "question": question,
        "answer": answer,
        "added_by": added_by,
        "added_at": datetime.utcnow().isoformat(),
        "question_topic": question_topic or "General",
        "question_source": question_source,
        "answer_source": answer_source,
        "media_path": media_path,
        "incorrect_answers": incorrect_answers or [],
        "times_asked": 0,
        "times_correctly_answered": 0,
        "times_incorrectly_answered": 0,
        "last_updated_at": datetime.utcnow().isoformat(),
        "language": language,
        "review_status": False,
        "tags": tags or []
    }
    table.put_item(Item=item)
    return question_id

# Fetch all questions
def get_all_questions():
    """Fetches all trivia questions from DynamoDB."""
    response = table.scan()
    return response.get("Items", [])

# Fetch a random question
def get_random_question():
    """Fetches a random question from DynamoDB."""
    response = table.scan()  # Get all questions
    items = response.get("Items", [])

    if not items:
        return None  # No questions available

    random_question = random.choice(items)  # Pick a random item
    return random_question

# Delete a question by ID
def delete_question(question_id, question_topic):
    """Deletes a question from DynamoDB by ID and question_topic."""
    try:
        table.delete_item(
            Key={
                "id": question_id,
                "question_topic": question_topic  # ✅ Required Sort Key
            }
        )
        return True
    except Exception as e:
        print(f"Error deleting question: {e}")
        return False


# List all files in the S3 bucket
def list_s3_files():
    """Lists all files in the S3 bucket."""
    response = s3.list_objects_v2(Bucket=AWS_S3_BUCKET)
    files = [file["Key"] for file in response.get("Contents", [])]
    return files

def upload_file_to_s3(file):
    """Uploads a file to S3 and returns the public URL."""
    if not file:
        print("DEBUG: No file received for upload.")
        return None
    
    # Extract file extension
    file_extension = file.filename.rsplit(".", 1)[-1].lower()
    
    # Only allow specific file types
    allowed_extensions = {"jpg", "jpeg", "png", "gif", "mp4", "mp3"}
    if file_extension not in allowed_extensions:
        print(f"DEBUG: File type {file_extension} not allowed.")
        return None  # Reject unsupported file types
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}.{file_extension}"

    print(f"DEBUG: Uploading file {file.filename} as {unique_filename} to S3...")

    # Determine MIME type
    content_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    try:
        # Upload to S3 with the correct Content-Type
        s3.upload_fileobj(
            file,
            AWS_S3_BUCKET,
            unique_filename,
            ExtraArgs={"ContentType": content_type}
        )
        
        file_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        print(f"DEBUG: File uploaded successfully: {file_url}")

        return file_url
    
    except Exception as e:
        print(f"ERROR: Failed to upload {file.filename} - {e}")
        return None
