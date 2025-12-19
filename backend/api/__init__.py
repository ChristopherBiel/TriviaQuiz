from .questions import questions_bp
from .users import users_bp
from .pages import pages_bp

__all__ = ["questions_bp", "users_bp", "pages_bp"]


def init_routes(app):
    app.register_blueprint(questions_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(pages_bp)
