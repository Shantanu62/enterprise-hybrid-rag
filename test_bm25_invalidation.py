
import tempfile
from pathlib import Path

from retrieval.rag_service import RAGService
from ingestion.pipeline import IngestionPipeline


TEST_FILENAME = "bm25_cache_test_unique.txt"
TEST_CONTENT = """
BM25CACHEVALIDATION is a unique enterprise testing keyword.
This document verifies that newly ingested documents become
available in the cached BM25 search index.
"""


def main():
    rag = RAGService()
    pipeline = None
    test_file = None

    try:
        manager = rag.search_service.bm25_index_manager

        print("\n========== BEFORE INGESTION ==========")

        manager.ensure_ready()

        before_documents = manager.get_documents()

        print("Documents before:", len(before_documents))

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / TEST_FILENAME
            test_file.write_text(TEST_CONTENT, encoding="utf-8")

            pipeline = IngestionPipeline(
                bm25_index_manager=manager
            )

            print("\n========== INGESTION ==========")

            result = pipeline.ingest_file(str(test_file))
            print("Ingestion result:", result)

            print("\n========== CACHE INVALIDATION ==========")

            print("Cache dirty:", manager._dirty)

            print("\n========== SEARCH AFTER INGESTION ==========")

            results = manager.search(
                query="BM25CACHEVALIDATION",
                limit=5,
            )

            after_documents = manager.get_documents()

            print("Documents after:", len(after_documents))
            print("Matching results:", len(results))

            for point_id, score in results:
                document = after_documents[point_id]
                print("Score:", round(score, 4))
                print("Text:", document["text"][:200])

            if results and any(
                "BM25CACHEVALIDATION" in after_documents[point_id]["text"]
                for point_id, _ in results
            ):
                print("\nPASS: Newly ingested document found in BM25.")
            else:
                print("\nFAIL: Newly ingested document not found.")

    finally:
        if pipeline is not None:
            pipeline.close()

        if test_file is not None:
            try:
                rag.search_service.vector_store.delete_document(
                    TEST_FILENAME
                )
                rag.search_service.bm25_index_manager.invalidate()
                print("\nTest document cleanup completed.")
            except Exception as exc:
                print("\nCleanup warning:", type(exc).__name__)

        rag.close()


if __name__ == "__main__":
    main()
