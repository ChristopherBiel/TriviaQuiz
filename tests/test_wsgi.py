from flask import Flask


def test_wsgi_app_is_flask_instance():
    import wsgi

    assert isinstance(wsgi.app, Flask)
