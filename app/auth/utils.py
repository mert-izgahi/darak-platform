# app/auth/utils.py
import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    bcrypt automatically handles salting — never do it manually.

    Returns a string (decoded from bytes for MongoDB storage).
    """
    password_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plain text password against a stored hash.
    Returns True if they match, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )
