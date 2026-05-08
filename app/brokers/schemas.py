# app/brokers/schemas.py
from marshmallow import Schema, fields, validate


class CreateProfileSchema(Schema):
    """Validates input when a broker creates their profile."""

    display_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    bio = fields.Str(validate=validate.Length(max=500), load_default="")
    whatsapp_number = fields.Str(validate=validate.Length(max=20), load_default="")
    city = fields.Str(validate=validate.Length(max=100), load_default="")


class UpdateProfileSchema(Schema):
    """Validates input when a broker updates their profile.
    All fields optional — only update what's sent."""

    display_name = fields.Str(validate=validate.Length(min=2, max=100))
    bio = fields.Str(validate=validate.Length(max=500))
    whatsapp_number = fields.Str(validate=validate.Length(max=20))
    city = fields.Str(validate=validate.Length(max=100))
