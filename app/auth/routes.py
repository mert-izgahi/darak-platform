# app/auth/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError
from .models import User
from .schemas import RegisterSchema, LoginSchema
from .utils import hash_password, verify_password

auth_bp = Blueprint("auth", __name__)

register_schema = RegisterSchema()
login_schema = LoginSchema()


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new broker account."""

    # Step 1 — validate input
    try:
        data = register_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # Step 2 — check if email already exists
    if User.objects(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    # Step 3 — create user with hashed password
    user = User(
        name=data["name"],
        email=data["email"],
        phone=data["phone"],
        password_hash=hash_password(data["password"]),
    )
    user.save()

    # Step 4 — generate JWT token
    # We store the user's string ID in the token
    access_token = create_access_token(identity=str(user.id))

    return (
        jsonify(
            {
                "message": "Account created successfully",
                "access_token": access_token,
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                },
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login with email and password, returns JWT token."""

    # Step 1 — validate input
    try:
        data = login_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # Step 2 — find user by email
    user = User.objects(email=data["email"]).first()

    # Step 3 — verify password
    # Note: we check user exists AND password matches in the same error
    # message — never reveal whether the email exists or not
    if not user or not verify_password(data["password"], user.password_hash):
        return jsonify({"error": "Invalid email or password"}), 401

    # Step 4 — check account is active
    if not user.is_active:
        return jsonify({"error": "Account is deactivated"}), 403

    # Step 5 — generate token
    access_token = create_access_token(identity=str(user.id))

    return (
        jsonify(
            {
                "message": "Login successful",
                "access_token": access_token,
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                },
            }
        ),
        200,
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    Returns the currently authenticated user's profile.
    Requires a valid JWT token in the Authorization header.
    """
    # get_jwt_identity() extracts the user ID we stored in the token
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return (
        jsonify(
            {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "created_at": user.created_at.isoformat(),
            }
        ),
        200,
    )
