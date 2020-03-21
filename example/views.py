# views.py
from flask import jsonify, request, current_app, g, Blueprint

from flask_apispec import docs
from flask_apispec.decorators import json_schema, headers_schema, querystring_schema

from .schemas import Message, User, UsersList

users = Blueprint("users", __name__)


@docs(
    tags=["users"],
    summary="Get users list",
    description="Get list of all users from our toy database",
    responses={
        200: {"description": "Ok. Users list", "schema": UsersList},
        404: {"description": "Not Found"},
        500: {"description": "Server error"},
    },
)
@users.route("/", methods=["GET"])
def get_users():
    return jsonify(items=current_app.users)


@docs(
    tags=["users"],
    summary="Get user",
    description="Get single user from our toy database",
    responses={
        200: {"description": "Ok. User", "schema": User},
        404: {"description": "Not Found"},
        500: {"description": "Server error"},
    },
)
@users.route("/<int:id>/", methods=["GET"])
def get_user(id: int):
    users = [u for u in current_app.users if u["id"] == id]
    return jsonify(users[0])


@docs(
    tags=["users"],
    summary="Create new user",
    description="Add new user to our toy database",
    responses={
        200: {"description": "Ok. User created", "schema": User},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        500: {"description": "Server error"},
    },
)
@json_schema(User)
@users.route("/", methods=["POST"])
def create_user():
    current_app.users.append(g.json)
    return g.json
