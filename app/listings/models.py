# app/listings/models.py
from mongoengine import (
    Document,
    EmbeddedDocument,
    StringField,
    FloatField,
    IntField,
    BooleanField,
    DateTimeField,
    ReferenceField,
    ListField,
    EmbeddedDocumentField,
)
from datetime import datetime
from app.brokers.models import BrokerProfile


class ListingType:
    APARTMENT = "apartment"
    VILLA = "villa"
    LAND = "land"
    COMMERCIAL = "commercial"
    OFFICE = "office"

    CHOICES = [
        (APARTMENT, "Apartment"),
        (VILLA, "Villa"),
        (LAND, "Land"),
        (COMMERCIAL, "Commercial"),
        (OFFICE, "Office"),
    ]


class ListingStatus:
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PAUSED = "paused"
    SOLD = "sold"

    CHOICES = [
        (ACTIVE, "Active"),
        (SUSPENDED, "Suspended"),
        (PAUSED, "Paused"),
        (SOLD, "Sold"),
    ]


class ListingPurpose:
    SALE = "sale"
    RENT = "rent"

    CHOICES = [
        (SALE, "Sale"),
        (RENT, "Rent"),
    ]


class Currency:
    USD = "USD"
    SYP = "SYP"

    CHOICES = [
        (USD, "US Dollar"),
        (SYP, "Syrian Pound"),
    ]


class ListingImage(EmbeddedDocument):
    """
    A single image attached to a listing.
    Stored as an embedded array — never as a separate collection.
    """

    url = StringField(required=True)  # Cloudinary delivery URL
    public_id = StringField(required=True)  # Cloudinary ID for deletion


class Listing(Document):
    """
    A real estate listing created by a broker.
    This is the core entity of the Darak platform.
    """

    meta = {
        "collection": "listings",
        "indexes": [
            "broker",
            "status",
            "city",
            "property_type",
            "purpose",
            "-created_at",  # descending — newest first
            ("city", "property_type", "purpose"),  # compound index
        ],
        # text index — enables keyword search
        "fields": ["$title", "$description", "$city", "$district"],
        "default_language": "none",  # "none" supports Arabic + English
    }

    # ── Ownership ─────────────────────────────
    broker = ReferenceField(BrokerProfile, required=True)

    # ── Core fields ───────────────────────────
    title = StringField(required=True, max_length=200)
    description = StringField(max_length=2000, default="")

    property_type = StringField(required=True, choices=ListingType.CHOICES)
    purpose = StringField(required=True, choices=ListingPurpose.CHOICES)

    # ── Pricing ───────────────────────────────
    price = FloatField(required=True, min_value=0)
    currency = StringField(default=Currency.USD, choices=Currency.CHOICES)

    # ── Location ──────────────────────────────
    city = StringField(required=True, max_length=100)
    district = StringField(max_length=100, default="")

    # ── Property details ──────────────────────
    area_sqm = FloatField(min_value=0, default=0)
    bedrooms = IntField(min_value=0, default=0)
    bathrooms = IntField(min_value=0, default=0)
    floor = IntField(default=0)
    furnished = BooleanField(default=False)

    # ── Media ─────────────────────────────────
    images = ListField(EmbeddedDocumentField(ListingImage), default=list)

    # ── Status & analytics ────────────────────
    status = StringField(default=ListingStatus.ACTIVE, choices=ListingStatus.CHOICES)
    views_count = IntField(default=0)

    # ── Timestamps ────────────────────────────
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f"<Listing {self.title}>"

    def to_dict(self, include_broker=False):
        """
        Convert a Listing document to a dictionary.
        This is useful for JSON responses in routes.
        """

        data = {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "property_type": self.property_type,
            "purpose": self.purpose,
            "price": self.price,
            "currency": self.currency,
            "city": self.city,
            "district": self.district,
            "area_sqm": self.area_sqm,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "floor": self.floor,
            "furnished": self.furnished,
            "status": self.status,
            "views_count": self.views_count,
            "images": [
                {"url": img.url, "public_id": img.public_id} for img in self.images
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if include_broker:
            data["broker"] = {
                "id": str(self.broker.id),
                "display_name": self.broker.display_name,
                "slug": self.broker.slug,
                "whatsapp_number": self.broker.whatsapp_number,
                "profile_image": self.broker.profile_image,
            }

        return data
