
from retrieval.hybrid_search import HybridSearchService


def main():
    service = HybridSearchService()

    try:
        print("\n========== FIRST SEARCH ==========")

        first_results = service.search(
            query="annual leave policy",
            limit=5,
        )

        print("Results:", len(first_results))
        print("Metrics:", service.last_metrics)

        first_rebuild_time = service.last_metrics.get(
            "bm25_rebuild_ms", 0.0
        )

        print("\n========== SECOND SEARCH ==========")

        second_results = service.search(
            query="annual leave policy",
            limit=5,
        )

        print("Results:", len(second_results))
        print("Metrics:", service.last_metrics)

        second_rebuild_time = service.last_metrics.get(
            "bm25_rebuild_ms", 0.0
        )

        print("\n========== CACHE TEST SUMMARY ==========")

        print("First rebuild time:", first_rebuild_time)
        print("Second rebuild time:", second_rebuild_time)

        if first_rebuild_time > 0 and second_rebuild_time == first_rebuild_time:
            print("BM25 cache appears to be reused.")
        else:
            print("Please inspect the metrics.")

    finally:
        service.close()


if __name__ == "__main__":
    main()
