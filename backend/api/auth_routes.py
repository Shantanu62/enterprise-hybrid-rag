import os
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


def build_login_response(user: dict[str, Any]) -> dict[str, Any]:
    """Build the standard authentication response for an active user."""

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


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(request: LoginRequest):
    """
    Authenticate a user and return their active organizations.
    """

    try:
        user = authenticate_user(
            email=str(request.email),
            password=request.password,
        )

        return build_login_response(user)

    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed or no active organization is assigned.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/demo-login",
    response_model=LoginResponse,
)
def demo_login():
    """
    Authenticate the dedicated public demo account.

    Demo credentials are stored only in environment variables and are
    never exposed to the frontend or included in source code.
    """

    demo_email = os.getenv("DEMO_EMAIL", "").strip()
    demo_password = os.getenv("DEMO_PASSWORD", "")

    if not demo_email or not demo_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live demo is currently unavailable.",
        )

    try:
        user = authenticate_user(
            email=demo_email,
            password=demo_password,
        )

        return build_login_response(user)

    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live demo is currently unavailable.",
        )