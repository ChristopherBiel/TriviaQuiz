# backend/main.py
from flask import Flask
from backend.core.config import Config
from backend.routes import init_routes
from backend.api import init_routes as init_api_routes
import os

def create_app():
    app = Flask(__name__, template_folder=os.path.abspath("templates"))
    app.config.from_object(Config)

    init_routes(app)
    init_api_routes(app)
    return app
