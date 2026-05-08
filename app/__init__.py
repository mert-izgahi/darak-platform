# app/__init__.py
from flask import Flask
from .config import config_map
from .extensions import init_extensions


def create_app(config_name="development"):
    """
    App factory — creates and configures the Flask application.

    Args:
        config_name: "development", "production", or "testing"

    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__)

    # Load config class
    app.config.from_object(config_map[config_name])

    # Initialize extensions (DB, JWT, Cloudinary)
    init_extensions(app)

    # Register blueprints — we'll add these as we build each feature
    # ── Blueprints ──────────────────────────────
    from .auth import auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")

    # ────────────────────────────────────────────
    @app.route("/health")
    def health_check():
        """Simple route to verify the app is running."""
        return {"status": "ok", "project": "Darak"}

    return app
