
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from backend.auth.service import (
    AuthenticationError,
    authenticate_user,
    create_user_access_token,
)
from database.connection import get_db_connection


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in_minutes: int
    user: dict[str, Any]
    organizations: list[dict[str, Any]]


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(request: LoginRequest):
    """
    Authenticate user and return their active organizations.
    """

    try:
        user = authenticate_user(
            email=str(request.email),
            password=request.password,
        )

        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    o.id,
                    o.name,
                    om.role
                FROM organization_members om
                JOIN organizations o
                    ON o.id = om.organization_id
                WHERE
                    om.user_id = %s
                    AND o.status = 'active'
                ORDER BY o.name;
                """,
                (user["id"],),
            ).fetchall()

        organizations = [
            {
                "id": str(row[0]),
                "name": row[1],
                "role": row[2],
            }
            for row in rows
        ]

        if not organizations:
            raise AuthenticationError(
                "No active organization membership found."
            )

        access_token = create_user_access_token(
            user_id=user["id"],
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in_minutes": 30,
            "user": user,
            "organizations": organizations,
        }

    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed or no active organization is assigned.",
            headers={"WWW-Authenticate": "Bearer"},
        )
