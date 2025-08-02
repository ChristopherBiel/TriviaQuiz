from .questions import questions_bp
from .events import events_bp
from .pages import pages_bp
from .admin import admin_bp

def init_routes(app):
    app.register_blueprint(questions_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(admin_bp)
