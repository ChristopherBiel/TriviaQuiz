from flask import Flask
from backend.config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Import and register routes
from backend.routes import init_routes
init_routes(app)
