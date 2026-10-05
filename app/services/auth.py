from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import JWT_ALGORITHM, JWT_EXPIRY_MINUTES, JWT_SECRET_KEY

# ──────────────────────────────────────────────
# PASSWORD HASHING
# ──────────────────────────────────────────────
# We use bcrypt directly instead of passlib for better compatibility.
# bcrypt is the industry standard for password hashing — it's slow ON PURPOSE.
# Why slow? If a hacker steals your database, they'd need to try
# millions of passwords. A slow hash makes each attempt take longer,
# making brute-force attacks impractical.


def hash_password(plain_password: str) -> str:
    """
    Convert a plain-text password into a bcrypt hash.

    Example:
        "mypassword123" → "$2b$12$Xk9z7..."

    This is a ONE-WAY operation. You cannot reverse it.
    """
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain-text password matches a stored hash.

    Used during login: the user sends their password, we hash it
    and compare with what's stored in the database.
    Returns True if they match, False otherwise.
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ──────────────────────────────────────────────
# JWT TOKEN MANAGEMENT
# ──────────────────────────────────────────────


def create_access_token(user_id: int, role: str) -> str:
    """
    Create a JWT token containing the user's ID and role.

    The token structure (before encoding):
    {
        "sub": "5",           ← subject (user ID as a string — JWT convention)
        "role": "student",    ← user's role
        "exp": 1693...        ← expiration timestamp
    }

    The token is SIGNED with our secret key. If anyone tampers with it
    (e.g., changes role from "student" to "admin"), the signature won't
    match and the server will reject it.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> dict | None:
    """
    Decode and verify a JWT token.

    Returns the payload dict if valid, or None if:
    - The token has expired
    - The token was tampered with
    - The token is malformed
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
