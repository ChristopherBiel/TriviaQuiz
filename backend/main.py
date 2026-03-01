# backend/main.py
from flask import Flask
from backend.core.config import Config
from backend.routes import init_routes
from backend.api import init_routes as init_api_routes
import os
from pathlib import Path

def create_app():
    app = Flask(__name__, template_folder=os.path.abspath("templates"))
    app.config.from_object(Config)

    _version_file = Path(__file__).parent.parent / "VERSION"
    _app_version = _version_file.read_text().strip() if _version_file.exists() else "dev"

    @app.context_processor
    def inject_version():
        return {"app_version": _app_version}

    init_routes(app)
    init_api_routes(app)
    return app
