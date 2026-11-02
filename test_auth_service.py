
from uuid import uuid4

from backend.auth.service import (
    register_user,
    authenticate_user,
    get_user_by_id,
    create_user_access_token,
    AuthenticationError,
)
from backend.auth.security import decode_access_token
from database.connection import get_db_connection


def main():
    test_email = f"auth-test-{uuid4().hex}@example.com"
    test_password = "TestPassword123!Secure"

    user_id = None

    try:
        # 1. Register a temporary user
        user = register_user(
            email=test_email,
            full_name="Authentication Test User",
            password=test_password,
        )

        user_id = user["id"]
        print("User registration: PASS")

        # 2. Authenticate with correct password
        authenticated_user = authenticate_user(
            test_email,
            test_password,
        )

        print("Correct password login: PASS")

        # 3. Reject incorrect password
        try:
            authenticate_user(
                test_email,
                "WrongPassword123!",
            )
            raise AssertionError("Wrong password was accepted.")

        except AuthenticationError:
            print("Wrong password rejection: PASS")

        # 4. Retrieve user profile
        profile = get_user_by_id(user_id)

        assert profile is not None
        assert profile["email"] == test_email

        print("User profile retrieval: PASS")

        # 5. Generate and verify JWT
        token = create_user_access_token(
            authenticated_user["id"]
        )

        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == user_id

        print("JWT generation and verification: PASS")

    finally:
        # 6. Remove temporary test user
        if user_id:
            with get_db_connection() as conn:
                conn.execute(
                    "DELETE FROM users WHERE id = %s",
                    (user_id,),
                )

            print("Test user cleanup: PASS")


if __name__ == "__main__":
    main()
