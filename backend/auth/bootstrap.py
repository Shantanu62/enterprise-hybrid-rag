
import re
from typing import Any
from uuid import uuid4

from psycopg.errors import UniqueViolation

from backend.auth.security import hash_password
from database.connection import get_db_connection


class BootstrapError(Exception):
    """Raised when initial organization bootstrap fails."""


def create_initial_owner(
    organization_name: str,
    organization_slug: str,
    owner_name: str,
    owner_email: str,
    owner_password: str,
) -> dict[str, Any]:
    """
    Atomically create the first organization and its Owner.

    This function is intended for a trusted, one-time bootstrap
    operation, not a public registration endpoint.
    """

    organization_name = organization_name.strip()
    organization_slug = organization_slug.strip().lower()
    owner_name = owner_name.strip()
    owner_email = owner_email.strip().lower()

    if not all([
        organization_name,
        organization_slug,
        owner_name,
        owner_email,
        owner_password,
    ]):
        raise ValueError("All bootstrap fields are required.")

    if not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        organization_slug,
    ):
        raise ValueError("Organization slug format is invalid.")

    if len(owner_password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    organization_id = uuid4()
    user_id = uuid4()
    membership_id = uuid4()

    password_hash = hash_password(owner_password)

    try:
        with get_db_connection() as conn:

            # Lock both tables to prevent concurrent bootstrap
            # and user creation while the initial Owner is created.
            conn.execute(
                "LOCK TABLE organizations, users IN EXCLUSIVE MODE"
            )

            existing_organization = conn.execute(
                "SELECT id FROM organizations LIMIT 1"
            ).fetchone()

            if existing_organization:
                raise BootstrapError(
                    "An organization already exists. "
                    "Initial bootstrap is disabled."
                )

            existing_user = conn.execute(
                "SELECT id FROM users LIMIT 1"
            ).fetchone()

            if existing_user:
                raise BootstrapError(
                    "Users already exist. "
                    "Initial bootstrap is disabled."
                )

            user = conn.execute(
                """
                INSERT INTO users (
                    id, email, full_name, password_hash, status
                )
                VALUES (%s, %s, %s, %s, 'active')
                RETURNING id, email, full_name;
                """,
                (
                    user_id,
                    owner_email,
                    owner_name,
                    password_hash,
                ),
            ).fetchone()

            organization = conn.execute(
                """
                INSERT INTO organizations (
                    id, name, slug, status
                )
                VALUES (%s, %s, %s, 'active')
                RETURNING id, name, slug;
                """,
                (
                    organization_id,
                    organization_name,
                    organization_slug,
                ),
            ).fetchone()

            conn.execute(
                """
                INSERT INTO organization_members (
                    id, organization_id, user_id, role
                )
                VALUES (%s, %s, %s, 'owner');
                """,
                (
                    membership_id,
                    organization_id,
                    user_id,
                ),
            )

        return {
            "user": {
                "id": str(user[0]),
                "email": user[1],
                "full_name": user[2],
            },
            "organization": {
                "id": str(organization[0]),
                "name": organization[1],
                "slug": organization[2],
            },
            "role": "owner",
        }

    except UniqueViolation as exc:
        raise BootstrapError(
            "The email or organization slug already exists."
        ) from exc
