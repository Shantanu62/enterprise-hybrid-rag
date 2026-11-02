
import pytest

from backend.auth.permissions import (
    AuthorizationError,
    VALID_ROLES,
    has_permission,
    require_permission,
)


def test_all_four_roles_exist():
    assert VALID_ROLES == {
        "owner",
        "admin",
        "member",
        "viewer",
    }


@pytest.mark.parametrize(
    "role,permission,expected",
    [
        # Owner permissions
        ("owner", "organization:delete", True),
        ("owner", "members:invite", True),
        ("owner", "documents:delete", True),

        # Admin permissions
        ("admin", "members:invite", True),
        ("admin", "documents:delete", True),
        ("admin", "organization:delete", False),

        # Member permissions
        ("member", "documents:upload", True),
        ("member", "search:execute", True),
        ("member", "documents:delete", False),
        ("member", "members:invite", False),

        # Viewer permissions
        ("viewer", "documents:read", True),
        ("viewer", "search:execute", True),
        ("viewer", "documents:upload", False),
        ("viewer", "documents:delete", False),
        ("viewer", "members:invite", False),

        # Invalid role
        ("superadmin", "documents:delete", False),
    ],
)
def test_role_permissions(role, permission, expected):
    assert has_permission(role, permission) is expected


def test_require_permission_allows_authorized_action():
    require_permission("owner", "organization:delete")


def test_require_permission_blocks_unauthorized_action():
    with pytest.raises(AuthorizationError):
        require_permission("viewer", "documents:delete")


def test_invalid_role_is_rejected():
    with pytest.raises(AuthorizationError):
        require_permission("unknown", "documents:read")
