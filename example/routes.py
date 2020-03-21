# routes.py
from flask import Flask

from .views import users


def setup_routes(app: Flask):
    app.register_blueprint(users, url_prefix="/users")
