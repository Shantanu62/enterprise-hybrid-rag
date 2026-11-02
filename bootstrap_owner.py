
from getpass import getpass

from backend.auth.bootstrap import (
    BootstrapError,
    create_initial_owner,
)


def main() -> None:
    print("\n=== Enterprise RAG: Initial Owner Setup ===\n")
    print("This is a one-time administrative operation.\n")

    organization_name = input("Organization name: ").strip()
    organization_slug = input(
        "Organization slug (example: acme-ai): "
    ).strip()

    owner_name = input("Owner full name: ").strip()
    owner_email = input("Owner email: ").strip()

    owner_password = getpass("Create owner password: ")
    confirm_password = getpass("Confirm owner password: ")

    if owner_password != confirm_password:
        print("\nError: Passwords do not match.")
        return

    try:
        result = create_initial_owner(
            organization_name=organization_name,
            organization_slug=organization_slug,
            owner_name=owner_name,
            owner_email=owner_email,
            owner_password=owner_password,
        )

        print("\nInitial Owner created successfully!")
        print(f"Organization: {result['organization']['name']}")
        print(f"Organization ID: {result['organization']['id']}")
        print(f"Owner: {result['user']['full_name']}")
        print(f"Owner Email: {result['user']['email']}")
        print(f"Role: {result['role']}")

    except (ValueError, BootstrapError) as exc:
        print(f"\nSetup failed: {exc}")

    except Exception:
        print(
            "\nAn unexpected error occurred. "
            "Check your database configuration and logs."
        )


if __name__ == "__main__":
    main()
