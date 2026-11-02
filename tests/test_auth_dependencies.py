
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.auth import dependencies


# Sample authenticated user
SAMPLE_USER = {
    "id": str(uuid4()),
    "email": "test@example.com",
    "full_name": "Test User",
    "status": "active",
}


# Sample organization membership
SAMPLE_MEMBERSHIP = {
    "user_id": SAMPLE_USER["id"],
    "email": SAMPLE_USER["email"],
    "organization_id": str(uuid4()),
    "organization_name": "Test Organization",
    "role": "owner",
}


# --------------------------------------------------
# Authentication tests
# --------------------------------------------------

def test_missing_bearer_token_returns_401():
    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_user(None)

    assert exc.value.status_code == 401
    assert exc.value.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_jwt_returns_401(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "decode_access_token",
        lambda token: None,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid-token",
    )

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_user(credentials)

    assert exc.value.status_code == 401


def test_valid_jwt_returns_active_user(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "decode_access_token",
        lambda token: {"sub": SAMPLE_USER["id"]},
    )

    monkeypatch.setattr(
        dependencies,
        "get_user_by_id",
        lambda user_id: SAMPLE_USER,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="valid-token",
    )

    result = dependencies.get_current_user(credentials)

    assert result == SAMPLE_USER


def test_inactive_or_missing_user_returns_401(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "decode_access_token",
        lambda token: {"sub": SAMPLE_USER["id"]},
    )

    monkeypatch.setattr(
        dependencies,
        "get_user_by_id",
        lambda user_id: None,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="valid-token",
    )

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_user(credentials)

    assert exc.value.status_code == 401


# --------------------------------------------------
# Organization authorization tests
# --------------------------------------------------

def test_owner_can_access_authorized_organization(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "get_user_membership",
        lambda user_id, organization_id: SAMPLE_MEMBERSHIP,
    )

    dependency = dependencies.require_org_permission(
        "documents:delete"
    )

    result = dependency(
        organization_id=SAMPLE_MEMBERSHIP["organization_id"],
        current_user=SAMPLE_USER,
    )

    assert result["user"] == SAMPLE_USER
    assert result["membership"] == SAMPLE_MEMBERSHIP
    assert result["role"] == "owner"


def test_non_member_cannot_access_organization(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "get_user_membership",
        lambda user_id, organization_id: None,
    )

    dependency = dependencies.require_org_permission(
        "documents:read"
    )

    with pytest.raises(HTTPException) as exc:
        dependency(
            organization_id=str(uuid4()),
            current_user=SAMPLE_USER,
        )

    assert exc.value.status_code == 403


def test_viewer_cannot_delete_documents(monkeypatch):
    viewer_membership = {
        **SAMPLE_MEMBERSHIP,
        "role": "viewer",
    }

    monkeypatch.setattr(
        dependencies,
        "get_user_membership",
        lambda user_id, organization_id: viewer_membership,
    )

    dependency = dependencies.require_org_permission(
        "documents:delete"
    )

    with pytest.raises(HTTPException) as exc:
        dependency(
            organization_id=viewer_membership["organization_id"],
            current_user=SAMPLE_USER,
        )

    assert exc.value.status_code == 403


def test_viewer_can_read_documents(monkeypatch):
    viewer_membership = {
        **SAMPLE_MEMBERSHIP,
        "role": "viewer",
    }

    monkeypatch.setattr(
        dependencies,
        "get_user_membership",
        lambda user_id, organization_id: viewer_membership,
    )

    dependency = dependencies.require_org_permission(
        "documents:read"
    )

    result = dependency(
        organization_id=viewer_membership["organization_id"],
        current_user=SAMPLE_USER,
    )

    assert result["role"] == "viewer"
    assert result["organization_id"] == viewer_membership["organization_id"]


def test_membership_is_checked_for_requested_organization(monkeypatch):
    requested_organization_id = str(uuid4())
    captured = {}

    def fake_get_membership(user_id, organization_id):
        captured["user_id"] = user_id
        captured["organization_id"] = organization_id
        return SAMPLE_MEMBERSHIP

    monkeypatch.setattr(
        dependencies,
        "get_user_membership",
        fake_get_membership,
    )

    dependency = dependencies.require_org_permission(
        "documents:read"
    )

    dependency(
        organization_id=requested_organization_id,
        current_user=SAMPLE_USER,
    )

    assert captured["user_id"] == SAMPLE_USER["id"]
    assert captured["organization_id"] == requested_organization_id
