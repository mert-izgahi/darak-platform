# app/leads/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from datetime import datetime

from app.auth.models import User
from app.brokers.models import BrokerProfile
from app.listings.models import Listing
from .models import Lead, LeadStatus, LeadSource
from .schemas import SubmitLeadSchema, UpdateLeadStatusSchema

leads_bp = Blueprint("leads", __name__)

submit_schema = SubmitLeadSchema()
status_schema = UpdateLeadStatusSchema()


def _get_broker_or_403(user_id):
    """Get broker profile or return 403 error tuple."""
    user = User.objects(id=user_id).first()
    if not user:
        return None, (jsonify({"error": "User not found"}), 404)
    broker = BrokerProfile.objects(user=user).first()
    if not broker:
        return None, (jsonify({"error": "Broker profile required"}), 403)
    return broker, None


def _serialize_lead(lead):
    """Convert a Lead document to a clean dictionary."""
    return {
        "id": str(lead.id),
        "listing_id": str(lead.listing.id) if lead.listing else None,
        "listing_title": lead.listing_title,
        "visitor_name": lead.visitor_name,
        "visitor_phone": lead.visitor_phone,
        "message": lead.message,
        "source": lead.source,
        "status": lead.status,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat(),
    }


# ── Submit lead (public — no auth) ───────────────────────


@leads_bp.route("/<listing_id>", methods=["POST"])
def submit_lead(listing_id):
    """
    A visitor submits their contact info on a listing page.
    No authentication required — visitors are anonymous.
    """
    # validate input
    try:
        data = submit_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({"errors": e.messages}), 400

    # find the listing
    try:
        listing = Listing.objects(id=listing_id).first()
    except Exception:
        return jsonify({"error": "Invalid listing ID"}), 400

    if not listing or listing.status != "active":
        return jsonify({"error": "Listing not found or inactive"}), 404

    # create lead — snapshot the title in case listing is deleted later
    lead = Lead(
        broker=listing.broker,
        listing=listing,
        listing_title=listing.title,  # snapshot
        visitor_name=data["visitor_name"],
        visitor_phone=data["visitor_phone"],
        message=data.get("message", ""),
        source=data.get("source", LeadSource.FORM),
    )
    lead.save()

    return (
        jsonify(
            {
                "message": "Your inquiry has been submitted successfully",
                "lead_id": str(lead.id),
            }
        ),
        201,
    )


# ── Broker inbox ──────────────────────────────────────────


@leads_bp.route("/inbox", methods=["GET"])
@jwt_required()
def get_inbox():
    """
    Broker's lead inbox — all leads for their listings.
    Supports filtering by status and pagination.
    """
    user_id = get_jwt_identity()
    broker, err = _get_broker_or_403(user_id)
    if err:
        return err

    # optional status filter
    status = request.args.get("status")
    filters = {"broker": broker}

    if status and status in LeadStatus.CHOICES:
        filters["status"] = status

    # pagination
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)
    offset = (page - 1) * per_page

    leads = Lead.objects(**filters).order_by("-created_at")
    total = leads.count()

    return (
        jsonify(
            {
                "leads": [
                    _serialize_lead(l) for l in leads.skip(offset).limit(per_page)
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


# ── Update lead status ────────────────────────────────────


@leads_bp.route("/<lead_id>/status", methods=["PUT"])
@jwt_required()
def update_lead_status(lead_id):
    """
    Broker marks a lead as contacted or closed.
    Only the broker who owns the lead can update it.
    """
    user_id = get_jwt_identity()
    broker, err = _get_broker_or_403(user_id)
    if err:
        return err

    try:
        lead = Lead.objects(id=lead_id).first()
    except Exception:
        return jsonify({"error": "Invalid lead ID"}), 400

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    # ownership check
    if str(lead.broker.id) != str(broker.id):
        return jsonify({"error": "Not authorized"}), 403

    try:
        data = status_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({"errors": e.messages}), 400

    lead.status = data["status"]
    lead.updated_at = datetime.utcnow()
    lead.save()

    return (
        jsonify({"message": "Lead status updated", "lead": _serialize_lead(lead)}),
        200,
    )


# ── Lead stats ────────────────────────────────────────────


@leads_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_lead_stats():
    """
    Quick summary of a broker's lead pipeline.
    Useful for a dashboard widget.
    """
    user_id = get_jwt_identity()
    broker, err = _get_broker_or_403(user_id)
    if err:
        return err

    total = Lead.objects(broker=broker).count()
    new = Lead.objects(broker=broker, status=LeadStatus.NEW).count()
    contacted = Lead.objects(broker=broker, status=LeadStatus.CONTACTED).count()
    closed = Lead.objects(broker=broker, status=LeadStatus.CLOSED).count()

    # breakdown by source
    form = Lead.objects(broker=broker, source=LeadSource.FORM).count()
    whatsapp = Lead.objects(broker=broker, source=LeadSource.WHATSAPP).count()
    phone = Lead.objects(broker=broker, source=LeadSource.PHONE).count()

    return (
        jsonify(
            {
                "total": total,
                "by_status": {"new": new, "contacted": contacted, "closed": closed},
                "by_source": {"form": form, "whatsapp": whatsapp, "phone": phone},
            }
        ),
        200,
    )
