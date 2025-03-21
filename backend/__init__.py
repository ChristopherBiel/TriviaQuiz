import os
from flask import Flask
from backend.config import Config

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))  # Ensure Flask finds templates
app.config.from_object(Config)

# Import and register routes
from backend.routes import init_routes
init_routes(app)
