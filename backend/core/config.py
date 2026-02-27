from backend.core.settings import get_settings

settings = get_settings()


class Config:
    SECRET_KEY = settings.secret_key
    UPLOAD_FOLDER = settings.upload_folder
    ALLOWED_EXTENSIONS = settings.allowed_extensions
