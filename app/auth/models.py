# app/auth/models.py
from mongoengine import Document, StringField, BooleanField, DateTimeField
from datetime import datetime


class User(Document):
    """
    Represents a registered user in Darak.
    Currently all users are brokers — role field allows future expansion.
    """

    meta = {
        "collection": "users",
        "indexes": ["email", "phone"],  # fast lookups on these fields
    }

    name = StringField(required=True, max_length=100)
    email = StringField(required=True, unique=True, max_length=200)
    phone = StringField(required=True, max_length=20)
    password_hash = StringField(required=True)
    role = StringField(default="broker", choices=["broker", "admin"])
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }
