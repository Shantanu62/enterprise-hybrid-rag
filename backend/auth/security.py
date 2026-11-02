
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from dotenv import load_dotenv

load_dotenv()


# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip()
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing. Configure it in your .env file."
    )

if JWT_ALGORITHM != "HS256":
    raise RuntimeError("Only HS256 is supported by this configuration.")

if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError("Token expiration must be greater than zero.")


# Argon2 password hasher
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Securely hash a user's password using Argon2."""

    if not isinstance(password, str) or not password:
        raise ValueError("Password must not be empty.")

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a plain password against its Argon2 hash."""

    if not plain_password or not hashed_password:
        return False

    try:
        return password_hasher.verify(
            hashed_password,
            plain_password,
        )
    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):
        return False


def create_access_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for an authenticated user."""

    if not user_id or not user_id.strip():
        raise ValueError("User ID must not be empty.")

    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Verify a JWT and return its payload, or None if invalid."""

    if not token or not token.strip():
        return None

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        if not payload.get("sub"):
            return None

        return payload

    except jwt.InvalidTokenError:
        return None
