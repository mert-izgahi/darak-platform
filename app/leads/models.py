# app/leads/models.py
from mongoengine import Document, StringField, DateTimeField, ReferenceField
from datetime import datetime
from app.brokers.models import BrokerProfile
from app.listings.models import Listing


class LeadSource:
    FORM = "form"
    WHATSAPP = "whatsapp"
    PHONE = "phone"

    CHOICES = [
        (FORM, "form"),
        (WHATSAPP, "whatsapp"),
        (PHONE, "phone"),
    ]


class LeadStatus:
    NEW = "new"
    CONTACTED = "contacted"
    CLOSED = "closed"

    CHOICES = [
        (NEW, "new"),
        (CONTACTED, "contacted"),
        (CLOSED, "closed"),
    ]


class Lead(Document):
    """
    Represents a visitor's expression of interest in a listing.

    Leads are the core CRM data for brokers on Darak.
    They track where interest came from and what happened next.
    """

    meta = {
        "collection": "leads",
        "indexes": [
            "broker",
            "listing",
            "status",
            "-created_at",
            ("broker", "status"),  # broker filtering by status
            ("broker", "-created_at"),  # broker inbox sorted by newest
        ],
    }

    # ── Ownership ─────────────────────────────────────────
    broker = ReferenceField(BrokerProfile, required=True)
    listing = ReferenceField(Listing, required=True)

    # ── Snapshot — survives listing deletion ──────────────
    listing_title = StringField(required=True, max_length=200)

    # ── Visitor info ──────────────────────────────────────
    visitor_name = StringField(required=True, max_length=100)
    visitor_phone = StringField(required=True, max_length=20)
    message = StringField(max_length=1000, default="")

    # ── Lead metadata ─────────────────────────────────────
    source = StringField(
        required=True, choices=LeadSource.CHOICES, default=LeadSource.FORM
    )
    status = StringField(default=LeadStatus.NEW, choices=LeadStatus.CHOICES)

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f"<Lead {self.visitor_name} → {self.listing_title}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "broker_id": str(self.broker.id),
            "listing_id": str(self.listing.id),
            "listing_title": self.listing_title,
            "visitor_name": self.visitor_name,
            "visitor_phone": self.visitor_phone,
            "message": self.message,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
