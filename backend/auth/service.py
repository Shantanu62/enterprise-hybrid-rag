
from typing import Any
from uuid import UUID, uuid4

from psycopg.errors import UniqueViolation

from backend.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from database.connection import get_db_connection


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class RegistrationError(Exception):
    """Raised when user registration fails."""


def register_user(
    email: str,
    full_name: str,
    password: str,
) -> dict[str, Any]:
    """Register a user without granting organization privileges."""

    email = email.strip().lower()
    full_name = full_name.strip()

    if not email or not full_name:
        raise ValueError("Email and full name are required.")

    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    user_id = uuid4()
    password_hash = hash_password(password)

    query = """
        INSERT INTO users (
            id,
            email,
            full_name,
            password_hash,
            status
        )
        VALUES (%s, %s, %s, %s, 'active')
        RETURNING id, email, full_name, status, created_at;
    """

    try:
        with get_db_connection() as conn:
            row = conn.execute(
                query,
                (
                    user_id,
                    email,
                    full_name,
                    password_hash,
                ),
            ).fetchone()

        return {
            "id": str(row[0]),
            "email": row[1],
            "full_name": row[2],
            "status": row[3],
            "created_at": row[4],
        }

    except UniqueViolation as exc:
        raise RegistrationError(
            "An account with this email already exists."
        ) from exc


def authenticate_user(
    email: str,
    password: str,
) -> dict[str, Any]:
    """Authenticate a user using email and password."""

    email = email.strip().lower()

    query = """
        SELECT id, email, full_name, password_hash, status
        FROM users
        WHERE email = %s;
    """

    with get_db_connection() as conn:
        user = conn.execute(query, (email,)).fetchone()

    if not user or not user[3]:
        raise AuthenticationError("Invalid email or password.")

    if user[4] != "active":
        raise AuthenticationError("Account is not active.")

    if not verify_password(password, user[3]):
        raise AuthenticationError("Invalid email or password.")

    return {
        "id": str(user[0]),
        "email": user[1],
        "full_name": user[2],
        "status": user[4],
    }


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Retrieve an active user by UUID."""

    try:
        parsed_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        return None

    query = """
        SELECT id, email, full_name, status, created_at
        FROM users
        WHERE id = %s AND status = 'active';
    """

    with get_db_connection() as conn:
        user = conn.execute(
            query,
            (parsed_user_id,),
        ).fetchone()

    if not user:
        return None

    return {
        "id": str(user[0]),
        "email": user[1],
        "full_name": user[2],
        "status": user[3],
        "created_at": user[4],
    }


def create_user_access_token(user_id: str) -> str:
    """Create an access token for an authenticated user."""

    return create_access_token(user_id)
