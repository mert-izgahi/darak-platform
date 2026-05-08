# app/brokers/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from datetime import datetime

from app.auth.models import User
from .models import BrokerProfile
from .schemas import CreateProfileSchema, UpdateProfileSchema
from .utils import generate_slug

brokers_bp = Blueprint("brokers", __name__)

create_schema = CreateProfileSchema()
update_schema = UpdateProfileSchema()


@brokers_bp.route("/profile", methods=["POST"])
@jwt_required()
def create_profile():
    """
    Create a broker profile for the currently authenticated user.
    A user can only have one profile.
    """
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # check if profile already exists
    if BrokerProfile.objects(user=user).first():
        return jsonify({"error": "Profile already exists"}), 409

    # validate input
    try:
        data = create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # generate unique slug
    existing_slugs = [p.slug for p in BrokerProfile.objects.only("slug")]
    slug = generate_slug(data["display_name"], existing_slugs)

    profile = BrokerProfile(
        user=user,
        display_name=data["display_name"],
        bio=data.get("bio", ""),
        whatsapp_number=data.get("whatsapp_number", ""),
        city=data.get("city", ""),
        slug=slug,
    )
    profile.save()

    return (
        jsonify(
            {
                "message": "Profile created successfully",
                "profile": profile.to_dict(public=True),
            }
        ),
        201,
    )


@brokers_bp.route("/profile/me", methods=["GET"])
@jwt_required()
def get_my_profile():
    """Get the authenticated broker's own profile."""
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()
    profile = BrokerProfile.objects(user=user).first()

    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    return jsonify(profile.to_dict(public=False)), 200


@brokers_bp.route("/profile/me", methods=["PUT"])
@jwt_required()
def update_my_profile():
    """Update the authenticated broker's own profile."""
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()
    profile = BrokerProfile.objects(user=user).first()

    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    try:
        data = update_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # only update fields that were actually sent
    for field, value in data.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    profile.save()

    return (
        jsonify(
            {
                "message": "Profile updated successfully",
                "profile": profile.to_dict(public=False),
            }
        ),
        200,
    )


@brokers_bp.route("/<slug>", methods=["GET"])
def get_public_profile(slug):
    """
    Public profile page — no authentication required.
    This is the page visitors see when a broker shares their profile link.
    """
    profile = BrokerProfile.objects(slug=slug).first()

    if not profile:
        return jsonify({"error": "Broker not found"}), 404

    return jsonify(profile.to_dict(public=True)), 200
