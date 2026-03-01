from .health import health_bp
from .media import media_bp
from .questions import questions_bp
from .users import users_bp

__all__ = ["questions_bp", "users_bp", "media_bp", "health_bp"]


def init_routes(app):
    app.register_blueprint(questions_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(health_bp)
