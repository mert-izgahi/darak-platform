# app/listings/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from datetime import datetime

from app.auth.models import User
from app.brokers.models import BrokerProfile
from .models import Listing
from .schemas import CreateListingSchema, UpdateListingSchema

listings_bp = Blueprint("listings", __name__)

create_schema = CreateListingSchema()
update_schema = UpdateListingSchema()


def _get_broker_or_404(user_id):
    """
    Helper: get the broker profile for a user.
    Returns (broker, error_response) tuple.
    If broker not found, error_response is set.
    """
    user = User.objects(id=user_id).first()
    if not user:
        return None, (jsonify({"error": "User not found"}), 404)

    broker = BrokerProfile.objects(user=user).first()
    if not broker:
        return None, (jsonify({"error": "Broker profile required"}), 403)

    return broker, None


# ── Create ───────────────────────────────────────────────


@listings_bp.route("/", methods=["POST"])
@jwt_required()
def create_listing():
    """Create a new listing. Requires an existing broker profile."""
    user_id = get_jwt_identity()
    broker, err = _get_broker_or_404(user_id)
    if err:
        return err

    try:
        data = create_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({"errors": e.messages}), 400

    listing = Listing(broker=broker, **data)
    listing.save()

    # keep listing_count accurate on the broker profile
    BrokerProfile.objects(id=broker.id).update_one(inc__listing_count=1)

    return (
        jsonify(
            {
                "message": "Listing created successfully",
                "listing": listing.to_dict(),
            }
        ),
        201,
    )


# ── Read: my listings ─────────────────────────────────────


@listings_bp.route("/my", methods=["GET"])
@jwt_required()
def get_my_listings():
    """Get all listings for the authenticated broker."""
    user_id = get_jwt_identity()
    broker, err = _get_broker_or_404(user_id)
    if err:
        return err

    listings = Listing.objects(broker=broker).order_by("-created_at")

    return (
        jsonify(
            {
                "listings": [l.to_dict(include_broker=False) for l in listings],
                "total": listings.count(),
            }
        ),
        200,
    )


# ── Read: single listing (public) ────────────────────────


@listings_bp.route("/<listing_id>", methods=["GET"])
def get_listing(listing_id):
    """
    Get a single listing by ID.
    Public — no auth required.
    Increments view count on every visit.
    """
    try:
        listing = Listing.objects(id=listing_id).first()
    except Exception:
        return jsonify({"error": "Invalid listing ID"}), 400

    if not listing or listing.status == "sold":
        return jsonify({"error": "Listing not found"}), 404

    # increment view count — atomic operation
    Listing.objects(id=listing.id).update_one(inc__views_count=1)
    listing.reload()

    return jsonify(listing.to_dict(include_broker=True)), 200


# ── Read: browse all (public + filters) ──────────────────


@listings_bp.route("/", methods=["GET"])
def browse_listings():
    """
    Browse listings with optional filters.
    Public — no auth required.

    Query params:
        city, property_type, purpose, min_price,
        max_price, page, per_page
    """
    # build filter from query params
    filters = {"status": "active"}

    city = request.args.get("city")
    property_type = request.args.get("property_type")
    purpose = request.args.get("purpose")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    if city:
        filters["city"] = city
    if property_type:
        filters["property_type"] = property_type
    if purpose:
        filters["purpose"] = purpose
    if min_price is not None:
        filters["price__gte"] = min_price
    if max_price is not None:
        filters["price__lte"] = max_price

    # pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 50)  # cap at 50 — never let clients request 10,000

    offset = (page - 1) * per_page
    listings = Listing.objects(**filters).order_by("-created_at")
    total = listings.count()

    return (
        jsonify(
            {
                "listings": [
                    l.to_dict(include_broker=False)
                    for l in listings.skip(offset).limit(per_page)
                ],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
            }
        ),
        200,
    )


# ── Update ────────────────────────────────────────────────


@listings_bp.route("/<listing_id>", methods=["PUT"])
@jwt_required()
def update_listing(listing_id):
    """Update a listing. Only the owning broker can do this."""
    user_id = get_jwt_identity()
    broker, err = _get_broker_or_404(user_id)
    if err:
        return err

    try:
        listing = Listing.objects(id=listing_id).first()
    except Exception:
        return jsonify({"error": "Invalid listing ID"}), 400

    if not listing:
        return jsonify({"error": "Listing not found"}), 404

    # ownership check — critical security step
    if str(listing.broker.id) != str(broker.id):
        return jsonify({"error": "Not authorized"}), 403

    try:
        data = update_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({"errors": e.messages}), 400

    for field, value in data.items():
        setattr(listing, field, value)

    listing.updated_at = datetime.utcnow()
    listing.save()

    return (
        jsonify(
            {
                "message": "Listing updated successfully",
                "listing": listing.to_dict(include_broker=True),
            }
        ),
        200,
    )


# ── Delete ────────────────────────────────────────────────


@listings_bp.route("/<listing_id>", methods=["DELETE"])
@jwt_required()
def delete_listing(listing_id):
    """Delete a listing. Only the owning broker can do this."""
    user_id = get_jwt_identity()
    broker, err = _get_broker_or_404(user_id)
    if err:
        return err

    try:
        listing = Listing.objects(id=listing_id).first()
    except Exception:
        return jsonify({"error": "Invalid listing ID"}), 400

    if not listing:
        return jsonify({"error": "Listing not found"}), 404

    # ownership check
    if str(listing.broker.id) != str(broker.id):
        return jsonify({"error": "Not authorized"}), 403

    listing.delete()

    # keep listing_count accurate
    BrokerProfile.objects(id=broker.id).update_one(dec__listing_count=1)

    return jsonify({"message": "Listing deleted successfully"}), 200
