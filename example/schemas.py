# schemas.py
from marshmallow import Schema, fields, validate


class Message(Schema):
    message = fields.String()


class User(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    gender = fields.String(validate=validate.OneOf(["f", "m"]))


class UsersList(Schema):
    items = fields.Nested(User(many=True))
