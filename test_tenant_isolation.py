
from retrieval.hybrid_search import HybridSearchService

ORG_A_ID = "61a95709-2c5b-4d6e-aed3-875d886b1450"
ORG_B_ID = "f2e38b10-9330-434b-a957-76f3b5b282ee"

B_MARKER = "TENANT_B_SECRET_MARKER_2026"


def main():
    search_service = HybridSearchService()

    try:
        print("\n========== TENANT ISOLATION TEST ==========\n")

        # Test 1: Search Organization B's unique marker
        print("1. Searching as Organization A...")
        results_a = search_service.search(
            query=B_MARKER,
            tenant_id=ORG_A_ID,
            limit=10,
        )

        print(f"Organization A results: {len(results_a)}")

        # Test 2: Search the same marker as Organization B
        print("\n2. Searching as Organization B...")
        results_b = search_service.search(
            query=B_MARKER,
            tenant_id=ORG_B_ID,
            limit=10,
        )

        print(f"Organization B results: {len(results_b)}")

        # Check tenant ownership in every returned result
        a_ownership_valid = all(
            result.get("metadata", {}).get("tenant_id") == ORG_A_ID
            for result in results_a
        )

        b_ownership_valid = all(
            result.get("metadata", {}).get("tenant_id") == ORG_B_ID
            for result in results_b
        )

        # Check whether B's unique marker appears in retrieved text
        def contains_marker(results):
            return any(
                B_MARKER in str(result.get("text", ""))
                for result in results
            )

        marker_visible_to_a = contains_marker(results_a)
        marker_visible_to_b = contains_marker(results_b)

        print("\n========== TEST RESULTS ==========")
        print("A returned only A-owned records:", a_ownership_valid)
        print("B returned only B-owned records:", b_ownership_valid)
        print("B marker visible to A:", marker_visible_to_a)
        print("B marker visible to B:", marker_visible_to_b)

        passed = (
            a_ownership_valid
            and b_ownership_valid
            and not marker_visible_to_a
            and marker_visible_to_b
        )

        print("\n==================================")
        print("FINAL RESULT:", "PASS" if passed else "FAIL")
        print("==================================")

        if not passed:
            raise AssertionError(
                "Tenant isolation test did not satisfy all checks."
            )

    finally:
        search_service.close()


if __name__ == "__main__":
    main()
