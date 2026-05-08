# app/extensions.py
from flask_jwt_extended import JWTManager
from mongoengine import connect
import cloudinary

# JWT manager — initialized without app yet
jwt = JWTManager()


def init_extensions(app):
    """
    Bind all extensions to the Flask app.
    Called once inside create_app().
    """
    # JWT
    jwt.init_app(app)

    # MongoDB — connect using URI from config
    connect(host=app.config["MONGODB_URI"])

    # Cloudinary
    cloudinary.config(
        cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=app.config["CLOUDINARY_API_KEY"],
        api_secret=app.config["CLOUDINARY_API_SECRET"],
    )
