# app/brokers/utils.py
import re
import uuid


def generate_slug(display_name: str, existing_slugs: list = None) -> str:
    """
    Generate a URL-safe slug from a display name.

    Examples:
        "Ahmed Ali"     → "ahmed-ali"
        "Ahmed Ali" (taken) → "ahmed-ali-a3f9"
        "محمد العلي"   → "broker-a3f9b2c1"  (Arabic fallback)
    """
    existing_slugs = existing_slugs or []

    # lowercase and replace spaces with hyphens
    slug = display_name.lower().strip()
    slug = re.sub(r"\s+", "-", slug)

    # remove anything that isn't a letter, number, or hyphen
    slug = re.sub(r"[^a-z0-9\-]", "", slug)

    # remove leading/trailing hyphens
    slug = slug.strip("-")

    # if slug is empty (e.g. Arabic name with no latin chars), use fallback
    if not slug:
        slug = "broker-" + uuid.uuid4().hex[:8]
        return slug

    # if slug already exists, append a short unique suffix
    if slug in existing_slugs:
        slug = slug + "-" + uuid.uuid4().hex[:4]

    return slug
