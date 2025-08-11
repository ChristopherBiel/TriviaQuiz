import os
import boto3
import uuid
import mimetypes

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "chris-trivia-media-bucket")

s3 = boto3.client("s3", region_name=AWS_REGION)

def upload_file_to_s3(file):
    """Uploads a file to S3 and returns the public URL."""
    if not file or not hasattr(file, "filename"):
        print("DEBUG: No file or missing filename attribute for upload.")
        return None

    # Extract file extension
    if "." in file.filename:
        file_extension = file.filename.rsplit(".", 1)[-1].lower()
    else:
        print("DEBUG: File has no extension.")
        return None

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
        # Ensure file pointer is at start
        if hasattr(file, "seek"):
            file.seek(0)

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
        print(f"ERROR: Failed to upload {getattr(file, 'filename', 'unknown file')} - {e}")
        return None