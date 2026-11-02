
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


def test_login_success():
    """A valid login should return an access token."""

    fake_user = {
        "id": "62223d52-41b1-49cc-8953-cbe2ed0fe0fb",
        "email": "test@example.com",
        "full_name": "Test User",
        "status": "active",
    }

    with (
        patch(
            "backend.api.auth_routes.authenticate_user",
            return_value=fake_user,
        ),
        patch(
            "backend.api.auth_routes.create_user_access_token",
            return_value="test-access-token",
        ),
    ):
        with TestClient(app) as client:
            response = client.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "TestPassword123!",
                },
            )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"] == "test-access-token"
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"


def test_login_invalid_credentials():
    """Invalid credentials should return HTTP 401."""

    from backend.auth.service import AuthenticationError

    with patch(
        "backend.api.auth_routes.authenticate_user",
        side_effect=AuthenticationError("Invalid email or password."),
    ):
        with TestClient(app) as client:
            response = client.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "WrongPassword123!",
                },
            )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_invalid_email_format():
    """An invalid email format should return HTTP 422."""

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={
                "email": "invalid-email",
                "password": "TestPassword123!",
            },
        )

    assert response.status_code == 422
