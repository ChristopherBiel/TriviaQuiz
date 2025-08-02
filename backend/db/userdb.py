import boto3
import os

# Initialize AWS Clients
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)