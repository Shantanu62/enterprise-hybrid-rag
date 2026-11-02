
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from backend.auth.permissions import (
    get_user_membership,
    has_permission,
)
from backend.auth.security import decode_access_token
from backend.auth.service import get_user_by_id


# Read Bearer token from the Authorization header.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict[str, Any]:
    """
    Validate the JWT and return the authenticated active user.
    """

    unauthorized_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized_error

    payload = decode_access_token(credentials.credentials)

    if payload is None:
        raise unauthorized_error

    user_id = payload.get("sub")

    if not user_id:
        raise unauthorized_error

    user = get_user_by_id(user_id)

    if user is None:
        raise unauthorized_error

    return user


def require_org_permission(
    permission: str,
) -> Callable[..., dict[str, Any]]:
    """
    Verify organization membership and required permission.

    The organization_id comes from the endpoint path.
    Membership and role are always checked against PostgreSQL.
    """

    def dependency(
        organization_id: UUID,
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:

        membership = get_user_membership(
            user_id=current_user["id"],
            organization_id=str(organization_id),
        )

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization.",
            )

        if not has_permission(
            membership["role"],
            permission,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return {
            "user": current_user,
            "membership": membership,
            "organization_id": membership["organization_id"],
            "role": membership["role"],
        }

    return dependency
