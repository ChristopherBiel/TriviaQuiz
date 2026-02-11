from .questions import questions_bp
from .users import users_bp

__all__ = ["questions_bp", "users_bp"]


def init_routes(app):
    app.register_blueprint(questions_bp)
    app.register_blueprint(users_bp)
