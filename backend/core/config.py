from backend.core.settings import get_settings

settings = get_settings()


class Config:
    SECRET_KEY = settings.secret_key
    UPLOAD_FOLDER = settings.upload_folder
    ALLOWED_EXTENSIONS = settings.allowed_extensions
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False   # Set True in production behind HTTPS
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
