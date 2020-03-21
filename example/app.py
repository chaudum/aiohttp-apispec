# app.py
from flask import Flask

from flask_apispec import setup_flask_apispec, validation_middleware

from .routes import setup_routes


def create_app() -> Flask:
    app = Flask(__name__)
    setup_routes(app)
    # In-memory toy-database:
    app.users = []

    setup_flask_apispec(app, swagger_path="/docs", static_path="/static")
    app.before_request(validation_middleware)

    return app
