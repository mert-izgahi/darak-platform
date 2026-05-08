# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # reads your .env file into environment variables


class Config:
    """Base configuration — shared across all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "fallback-jwt-key")
    MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/darak_dev")

    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours in seconds


class DevelopmentConfig(Config):
    """Development — debug on, local database."""

    DEBUG = True


class ProductionConfig(Config):
    """Production — debug off, strict settings."""

    DEBUG = False


class TestingConfig(Config):
    """Testing — separate database, no real side effects."""

    TESTING = True
    MONGODB_URI = "mongodb://localhost:27017/darak_test"


# This dictionary lets us select config by name string
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

# Default is development
config_name = os.getenv("FLASK_ENV", "development")
config = config_map.get(config_name, DevelopmentConfig)
