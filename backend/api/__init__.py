from .questions import questions_bp

__all__ = ["questions_bp"]


def init_routes(app):
    app.register_blueprint(questions_bp)
