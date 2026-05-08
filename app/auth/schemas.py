# app/auth/schemas.py
from marshmallow import Schema, fields, validate, ValidationError


class RegisterSchema(Schema):
    """Validates input for the /auth/register endpoint."""

    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    phone = fields.Str(required=True, validate=validate.Length(min=7, max=20))
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8),
        load_only=True,  # never include password in serialized output
    )


class LoginSchema(Schema):
    """Validates input for the /auth/login endpoint."""

    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
