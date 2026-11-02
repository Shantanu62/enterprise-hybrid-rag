
from uuid import UUID

from database.connection import get_db_connection


# Roles allowed in the application
VALID_ROLES = {
    "owner",
    "admin",
    "member",
    "viewer",
}


# Define which actions each role can perform
ROLE_PERMISSIONS = {
    "owner": {
        "organization:read",
        "organization:update",
        "organization:delete",
        "members:read",
        "members:invite",
        "members:update_role",
        "members:remove",
        "documents:upload",
        "documents:read",
        "documents:update",
        "documents:delete",
        "search:execute",
    },

    "admin": {
        "organization:read",
        "members:read",
        "members:invite",
        "members:update_role",
        "members:remove",
        "documents:upload",
        "documents:read",
        "documents:update",
        "documents:delete",
        "search:execute",
    },

    "member": {
        "organization:read",
        "documents:upload",
        "documents:read",
        "search:execute",
    },

    "viewer": {
        "organization:read",
        "documents:read",
        "search:execute",
    },
}


class AuthorizationError(Exception):
    """Raised when a user does not have required permissions."""


def get_user_membership(
    user_id: str,
    organization_id: str,
) -> dict | None:
    """Return active organization membership for an active user."""

    try:
        parsed_user_id = UUID(user_id)
        parsed_organization_id = UUID(organization_id)
    except (ValueError, TypeError, AttributeError):
        return None

    query = """
        SELECT
            u.id,
            u.email,
            o.id,
            o.name,
            om.role
        FROM users u
        JOIN organization_members om
            ON om.user_id = u.id
        JOIN organizations o
            ON o.id = om.organization_id
        WHERE
            u.id = %s
            AND o.id = %s
            AND u.status = 'active'
            AND o.status = 'active';
    """

    with get_db_connection() as conn:
        result = conn.execute(
            query,
            (
                parsed_user_id,
                parsed_organization_id,
            ),
        ).fetchone()

    if not result:
        return None

    return {
        "user_id": str(result[0]),
        "email": result[1],
        "organization_id": str(result[2]),
        "organization_name": result[3],
        "role": result[4],
    }


def has_permission(
    role: str,
    permission: str,
) -> bool:
    """Check whether a role has a specific permission."""

    if role not in VALID_ROLES:
        return False

    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(
    role: str,
    permission: str,
) -> None:
    """Raise an error when the role lacks the requested permission."""

    if not has_permission(role, permission):
        raise AuthorizationError(
            f"Role '{role}' cannot perform '{permission}'."
        )
