
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app
from backend.auth.dependencies import get_current_user


SAMPLE_USER = {
    "id": str(uuid4()),
    "email": "owner@example.com",
    "full_name": "Test Owner",
    "status": "active",
}

ORGANIZATION_ID = str(uuid4())

OWNER_MEMBERSHIP = {
    "user_id": SAMPLE_USER["id"],
    "email": SAMPLE_USER["email"],
    "organization_id": ORGANIZATION_ID,
    "organization_name": "Test Organization",
    "role": "owner",
}

VIEWER_MEMBERSHIP = {
    **OWNER_MEMBERSHIP,
    "role": "viewer",
}


def test_owner_can_access_organization():
    app.dependency_overrides[get_current_user] = lambda: SAMPLE_USER

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=OWNER_MEMBERSHIP,
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/organizations/{ORGANIZATION_ID}/access-check"
                )

        assert response.status_code == 200
        data = response.json()
        assert data["organization"]["role"] == "owner"
        assert data["organization"]["name"] == "Test Organization"

    finally:
        app.dependency_overrides.clear()


def test_owner_can_access_admin_check():
    app.dependency_overrides[get_current_user] = lambda: SAMPLE_USER

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=OWNER_MEMBERSHIP,
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/organizations/{ORGANIZATION_ID}/admin-check"
                )

        assert response.status_code == 200
        assert response.json()["role"] == "owner"

    finally:
        app.dependency_overrides.clear()


def test_missing_token_returns_401():
    with TestClient(app) as client:
        response = client.get(
            f"/organizations/{ORGANIZATION_ID}/access-check"
        )

    assert response.status_code == 401


def test_non_member_returns_403():
    app.dependency_overrides[get_current_user] = lambda: SAMPLE_USER

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=None,
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/organizations/{ORGANIZATION_ID}/access-check"
                )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()


def test_viewer_cannot_access_admin_check():
    app.dependency_overrides[get_current_user] = lambda: SAMPLE_USER

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=VIEWER_MEMBERSHIP,
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/organizations/{ORGANIZATION_ID}/admin-check"
                )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()
