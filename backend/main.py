# backend/main.py
from flask import Flask
from backend.core.config import Config
from backend.routes import init_routes
from backend.api import init_routes as init_api_routes
import json
import os
from pathlib import Path


def _load_legal_config() -> dict:
    """Load legal_config.json from the project root if present."""
    config_path = Path(__file__).parent.parent / "legal_config.json"
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def create_app():
    app = Flask(__name__,
                template_folder=os.path.abspath("templates"),
                static_folder=os.path.abspath("static"),
                static_url_path="/static")
    app.config.from_object(Config)

    _version_file = Path(__file__).parent.parent / "VERSION"
    _app_version = _version_file.read_text().strip() if _version_file.exists() else "dev"
    _legal = _load_legal_config()

    @app.context_processor
    def inject_globals():
        return {"app_version": _app_version, "legal": _legal}

    init_routes(app)
    init_api_routes(app)
    return app
