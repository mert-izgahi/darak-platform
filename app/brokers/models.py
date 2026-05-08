# app/brokers/models.py
from mongoengine import (
    Document,
    StringField,
    BooleanField,
    DateTimeField,
    ReferenceField,
    IntField,
)
from datetime import datetime
from app.auth.models import User


class BrokerProfile(Document):
    """
    Public profile for a broker on Darak.
    Linked to a User via reference — one profile per user.
    """

    meta = {"collection": "broker_profiles", "indexes": ["user", "slug", "city"]}

    user = ReferenceField(User, required=True, unique=True)
    display_name = StringField(required=True, max_length=100)
    bio = StringField(max_length=500, default="")
    whatsapp_number = StringField(max_length=20, default="")
    city = StringField(max_length=100, default="")
    profile_image = StringField(default="")  # Cloudinary URL
    slug = StringField(required=True, unique=True, max_length=120)
    listing_count = IntField(default=0)
    verified = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f"<BrokerProfile {self.slug}>"

    def to_dict(self, public=False):
        """
        Convert a BrokerProfile document to a dictionary.

        Why a helper function?
        We serialize profiles in multiple routes — keeping it DRY.
        The `public` flag hides sensitive fields from public responses.
        """
        if public:
            # include only public fields
            return {
                "display_name": self.display_name,
                "bio": self.bio,
                "city": self.city,
                "profile_image": self.profile_image,
                "slug": self.slug,
                "listing_count": self.listing_count,
                "verified": self.verified,
            }
        return {
            "id": str(self.id),
            "user_id": str(self.user.id),
            "display_name": self.display_name,
            "bio": self.bio,
            "whatsapp_number": self.whatsapp_number,
            "city": self.city,
            "profile_image": self.profile_image,
            "slug": self.slug,
            "listing_count": self.listing_count,
            "verified": self.verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
