
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from backend.auth.service import (
    AuthenticationError,
    authenticate_user,
    create_user_access_token,
)


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


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(request: LoginRequest):
    """
    Authenticate a user and return a JWT access token.
    """

    try:
        user = authenticate_user(
            email=str(request.email),
            password=request.password,
        )

        access_token = create_user_access_token(
            user_id=user["id"],
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in_minutes": 30,
            "user": user,
        }

    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
