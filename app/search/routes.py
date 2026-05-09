# app/search/routes.py
from flask import Blueprint, request, jsonify
from app.listings.models import Listing
from app.brokers.models import BrokerProfile

search_bp = Blueprint("search", __name__)


# ── Helper ────────────────────────────────────────────────


def _serialize_listing_card(listing):
    """
    Lightweight listing serializer for search results.

    Why lighter than the full serializer in listings/routes.py?
    Search returns many results — you don't need every field.
    Send only what the UI card needs: title, price, city, one image.
    Less data = faster response = better mobile experience.
    """
    return {
        "id": str(listing.id),
        "title": listing.title,
        "property_type": listing.property_type,
        "purpose": listing.purpose,
        "price": listing.price,
        "currency": listing.currency,
        "city": listing.city,
        "district": listing.district,
        "area_sqm": listing.area_sqm,
        "bedrooms": listing.bedrooms,
        "bathrooms": listing.bathrooms,
        "furnished": listing.furnished,
        "thumbnail": listing.images[0].url if listing.images else None,
        "broker": {
            "display_name": listing.broker.display_name,
            "slug": listing.broker.slug,
            "whatsapp_number": listing.broker.whatsapp_number,
        },
        "created_at": listing.created_at.isoformat(),
    }


def _serialize_broker_card(profile):
    """Lightweight broker serializer for discovery results."""
    return {
        "id": str(profile.id),
        "display_name": profile.display_name,
        "city": profile.city,
        "bio": profile.bio,
        "profile_image": profile.profile_image,
        "slug": profile.slug,
        "listing_count": profile.listing_count,
        "verified": profile.verified,
        "whatsapp_number": profile.whatsapp_number,
    }


# ── Main search endpoint ──────────────────────────────────


@search_bp.route("/", methods=["GET"])
def search():
    """
    Unified search endpoint for listings.

    Query params:
        q            — keyword search (title, description, city)
        city         — filter by city
        property_type — apartment | villa | land | commercial | office
        purpose      — sale | rent
        min_price    — minimum price
        max_price    — maximum price
        min_bedrooms — minimum bedroom count
        furnished    — true | false
        sort         — newest | price_asc | price_desc
        page         — page number (default 1)
        per_page     — results per page (default 20, max 50)

    Example:
        /search/?q=شقة&city=Damascus&purpose=sale&min_price=50000
    """
    filters = {"status": "active"}

    # ── Keyword search ──────────────────────────
    q = request.args.get("q", "").strip()

    # ── Field filters ───────────────────────────
    city = request.args.get("city", "").strip()
    property_type = request.args.get("property_type", "").strip()
    purpose = request.args.get("purpose", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    min_bedrooms = request.args.get("min_bedrooms", type=int)
    furnished = request.args.get("furnished", "").strip().lower()

    if city:
        filters["city__icontains"] = city  # case-insensitive match
    if property_type:
        filters["property_type"] = property_type
    if purpose:
        filters["purpose"] = purpose
    if min_price is not None:
        filters["price__gte"] = min_price
    if max_price is not None:
        filters["price__lte"] = max_price
    if min_bedrooms is not None:
        filters["bedrooms__gte"] = min_bedrooms
    if furnished == "true":
        filters["furnished"] = True
    elif furnished == "false":
        filters["furnished"] = False

    # ── Sorting ─────────────────────────────────
    sort = request.args.get("sort", "newest")
    sort_map = {
        "newest": "-created_at",
        "price_asc": "price",
        "price_desc": "-price",
    }
    order_by = sort_map.get(sort, "-created_at")

    # ── Pagination ──────────────────────────────
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)
    offset = (page - 1) * per_page

    # ── Execute query ───────────────────────────
    try:
        if q:
            # text search — use PyMongo directly for $text operator
            # MongoEngine doesn't expose $text cleanly, so we drop down
            collection = Listing._get_collection()
            text_filter = {"$text": {"$search": q}, **_build_pymongo_filters(filters)}

            cursor = (
                collection.find(text_filter, {"score": {"$meta": "textScore"}})
                .sort([("score", {"$meta": "textScore"})])
                .skip(offset)
                .limit(per_page)
            )

            total = collection.count_documents(text_filter)
            listing_ids = [doc["_id"] for doc in cursor]
            listings = Listing.objects(id__in=listing_ids)

            # preserve text score order
            listings_by_id = {str(l.id): l for l in listings}
            ordered = [
                listings_by_id[str(lid)]
                for lid in listing_ids
                if str(lid) in listings_by_id
            ]
        else:
            queryset = Listing.objects(**filters).order_by(order_by)
            total = queryset.count()
            ordered = list(queryset.skip(offset).limit(per_page))

    except Exception as e:
        return jsonify({"error": "Search failed", "detail": str(e)}), 500

    return (
        jsonify(
            {
                "results": [_serialize_listing_card(l) for l in ordered],
                "query": {
                    "q": q,
                    "city": city,
                    "property_type": property_type,
                    "purpose": purpose,
                    "sort": sort,
                },
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page if total else 0,
                },
            }
        ),
        200,
    )


def _build_pymongo_filters(mongoengine_filters: dict) -> dict:
    """
    Convert MongoEngine filter kwargs to raw PyMongo filter dict.
    Needed because we drop down to PyMongo for $text search.

    Examples:
        {"status": "active", "price__gte": 50000}
        → {"status": "active", "price": {"$gte": 50000}}
    """
    operator_map = {
        "gte": "$gte",
        "lte": "$lte",
        "gt": "$gt",
        "lt": "$lt",
        "ne": "$ne",
    }

    pymongo_filter = {}

    for key, value in mongoengine_filters.items():
        if "__" in key:
            parts = key.split("__")
            field = parts[0]
            op = parts[1]

            if op == "icontains":
                import re

                pymongo_filter[field] = {"$regex": re.escape(value), "$options": "i"}
            elif op in operator_map:
                pymongo_filter[field] = {operator_map[op]: value}
        else:
            pymongo_filter[key] = value

    return pymongo_filter


# ── Discovery endpoints ───────────────────────────────────


@search_bp.route("/cities", methods=["GET"])
def get_cities():
    """
    Return all cities that have active listings, with counts.
    Used to build the city browse UI.

    Why aggregate instead of a hardcoded list?
    The platform is data-driven — cities appear as brokers add listings.
    No manual configuration needed.
    """
    try:
        collection = Listing._get_collection()
        pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {"_id": "$city", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},  # most listings first
            {"$project": {"_id": 0, "city": "$_id", "listing_count": "$count"}},
        ]
        cities = list(collection.aggregate(pipeline))
    except Exception as e:
        return jsonify({"error": "Failed to fetch cities", "detail": str(e)}), 500

    return jsonify({"cities": cities}), 200


@search_bp.route("/categories", methods=["GET"])
def get_categories():
    """
    Return listing counts grouped by property_type and purpose.
    Used to build the category browse UI.

    Example response:
        apartment: { sale: 45, rent: 23 }
        villa:     { sale: 12, rent: 5  }
    """
    try:
        collection = Listing._get_collection()
        pipeline = [
            {"$match": {"status": "active"}},
            {
                "$group": {
                    "_id": {"type": "$property_type", "purpose": "$purpose"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
        ]
        raw = list(collection.aggregate(pipeline))
    except Exception as e:
        return jsonify({"error": "Failed to fetch categories", "detail": str(e)}), 500

    # reshape into a nested structure
    categories = {}
    for item in raw:
        prop_type = item["_id"]["type"]
        purpose = item["_id"]["purpose"]
        count = item["count"]

        if prop_type not in categories:
            categories[prop_type] = {}
        categories[prop_type][purpose] = count

    return jsonify({"categories": categories}), 200


@search_bp.route("/brokers", methods=["GET"])
def discover_brokers():
    """
    Browse and search brokers.

    Query params:
        city     — filter by city
        q        — search by display name
        page, per_page
    """
    filters = {}

    city = request.args.get("city", "").strip()
    q = request.args.get("q", "").strip()

    if city:
        filters["city__icontains"] = city
    if q:
        filters["display_name__icontains"] = q

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)
    offset = (page - 1) * per_page

    profiles = BrokerProfile.objects(**filters).order_by("-listing_count")
    total = profiles.count()

    return (
        jsonify(
            {
                "brokers": [
                    _serialize_broker_card(p)
                    for p in profiles.skip(offset).limit(per_page)
                ],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page if total else 0,
                },
            }
        ),
        200,
    )
