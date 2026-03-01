from __future__ import annotations

import mimetypes
import uuid
from urllib.parse import quote, urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from backend.core.settings import get_settings
from backend.storage.base import MediaStore


class MinioMediaStore(MediaStore):
    def __init__(self) -> None:
        settings = get_settings()
        endpoint = settings.minio_endpoint
        if endpoint and "://" not in endpoint:
            scheme = "https" if settings.minio_secure else "http"
            endpoint = f"{scheme}://{endpoint}"

        self._settings = settings
        self._bucket = settings.minio_bucket
        self._endpoint = endpoint
        self._endpoint_host = urlparse(endpoint).netloc if endpoint else ""
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name=settings.minio_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def _ensure_bucket(self) -> None:
        if not self._settings.minio_auto_create_bucket:
            return
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            code = (exc.response.get("Error") or {}).get("Code")
            if code in {"404", "NoSuchBucket", "NotFound"}:
                self._client.create_bucket(Bucket=self._bucket)
            else:
                raise

    def _extract_key(self, media_path: str | None) -> str | None:
        if not media_path:
            return None

        if media_path.startswith("s3://") or media_path.startswith("minio://"):
            _, _, path = media_path.partition("://")
            parts = path.split("/", 1)
            if len(parts) == 2:
                return parts[1]
            return None

        parsed = urlparse(media_path)
        if parsed.scheme in {"http", "https"}:
            key = parsed.path.lstrip("/")
            if key.startswith(f"{self._bucket}/"):
                key = key[len(self._bucket) + 1 :]
            return key or None

        return media_path

    def _should_return_original_url(self, media_path: str) -> bool:
        parsed = urlparse(media_path)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            if self._endpoint_host and parsed.netloc != self._endpoint_host:
                return True
        return False

    def upload(self, file):
        if not file or not hasattr(file, "filename"):
            return None

        if "." in file.filename:
            file_extension = file.filename.rsplit(".", 1)[-1].lower()
        else:
            return None

        if file_extension not in self._settings.allowed_extensions:
            return None

        key = f"{uuid.uuid4()}.{file_extension}"
        content_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

        try:
            if hasattr(file, "seek"):
                file.seek(0)
            self._ensure_bucket()
            self._client.upload_fileobj(
                file,
                self._bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            return key
        except ClientError:
            return None

    def delete(self, media_path: str) -> bool:
        key = self._extract_key(media_path)
        if not key:
            return False
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    def get_url(self, media_path: str, expires_in: int | None = None):
        if not media_path:
            return None
        if self._should_return_original_url(media_path):
            return media_path
        key = self._extract_key(media_path)
        if not key:
            return None

        if self._settings.media_proxy:
            return f"/media/{quote(key)}"

        ttl = expires_in or self._settings.media_url_expires_seconds
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=ttl,
            )
        except ClientError:
            return None

    def download(self, media_path: str):
        key = self._extract_key(media_path)
        if not key:
            raise FileNotFoundError("Missing media key")
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = (exc.response.get("Error") or {}).get("Code")
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise FileNotFoundError("Media not found") from exc
            raise
        return obj.get("Body"), obj.get("ContentType"), obj.get("ContentLength")
